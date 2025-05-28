import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, BaseFilter
from aiogram.types import Message

import predictor
from db import init_db, get_message_status, set_message_status

TOKEN = getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

dp = Dispatcher()
async_session, init_tables = init_db()

async def is_chat_admin(message: Message) -> bool:
    """
    Check if the user is an admin in the chat.
    """
    if not message.chat or not message.from_user:
        return False
    member = await message.chat.get_member(message.from_user.id)
    chat_admins = await message.chat.get_administrators()
    return member in chat_admins

class ServiceMessageFilter(BaseFilter):
    """
    A filter to identify service messages.
    """
    async def __call__(self, message: Message) -> bool:
        return any([
            message.new_chat_members,
            message.left_chat_member,
        ])

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(
        "Привет! Добавь меня в группу, дай права на удаление сообщений, и я избавлю тебя от спама!"
    )

@dp.message(ServiceMessageFilter())
async def delete_service_messages(message: Message) -> None:
    """
    Handler for service messages. Deletes the message.
    """
    try:
        await message.delete()
        logging.info(f"Deleted service message in chat {message.chat.id} from user {message.from_user.id}")
    except Exception as e:
        logging.error(f"Failed to delete service message: {e}")


@dp.message(Command("check"))
async def check_handler(message: Message) -> None:
    """
    Handler to check the message ignoring the user nonspam status
    """
    if not await is_chat_admin(message):
        return
    logging.info("Handling check for admin %s(%s)", message.from_user.full_name, message.from_user.id)
    if message.reply_to_message and message.reply_to_message.text:
        is_spam = predictor.predict(message.reply_to_message.text)
        if is_spam:
            answer_text = "Спам удален🥳\n"
            await message.reply_to_message.delete()
            if not await is_chat_admin(message.reply_to_message):
                await message.chat.ban(message.reply_to_message.from_user.id)
                answer_text += "Нарушитель забанен🥰\n"
            await message.answer(
                answer_text,
                reply_to_message_id=message.message_id,
                parse_mode=ParseMode.HTML,
            )
            logging.info(
                'Deleted spam message: "%s" from user %s(%s)',
                message.reply_to_message.text,
                message.reply_to_message.from_user.full_name,
                message.reply_to_message.from_user.id,
            )
            async with async_session() as session:
                await set_message_status(
                    session,
                    message.reply_to_message.chat.id,
                    message.reply_to_message.from_user.id,
                    False,
                )
        else:
            await message.answer(
                "Это сообщение не является спамом🥺",
                reply_to_message_id=message.message_id,
                parse_mode=ParseMode.HTML,
            )
    else:
        await message.answer(
            "Пожалуйста, ответьте на текстовое сообщение, которое вы хотите проверить на спам🤓",
            reply_to_message_id=message.message_id,
            parse_mode=ParseMode.HTML,
        )


@dp.message()
async def main_handler(message: Message) -> None:
    """
    Handler will detect spam messages and delete them, if the user has no non-spam messages
    """
    if message.text:
        is_spam = predictor.predict(message.text)
        async with async_session() as session:
            if not is_spam:
                await set_message_status(
                    session, message.chat.id, message.from_user.id, True
                )
            else:
                logging.info(
                    'Detected spam message: "%s" from user %s(%s)',
                    message.text,
                    message.from_user.full_name,
                    message.from_user.id,
                )
                if not await get_message_status(
                    session, message.chat.id, message.from_user.id
                ):
                    logging.info(
                        "User %s(%s) has no non-spam messages, deleting spam message and banning user",
                        message.from_user.full_name,
                        message.from_user.id,
                    )
                    await message.delete()
                    if not await is_chat_admin(message):
                        await message.chat.ban(message.from_user.id)

async def main() -> None:
    await init_tables()

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await dp.start_polling(bot, allowed_updates=["message", "chat_member"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
