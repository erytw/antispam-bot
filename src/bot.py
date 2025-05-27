import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

import predictor
from db import init_db, get_message_status, set_message_status

TOKEN = getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

dp = Dispatcher()
async_session, init_tables = init_db()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(
        "Привет! Добавь меня в группу, дай права на удаление сообщений, и я избавлю тебя от спама!"
    )


@dp.message(Command("check"))
async def check_handler(message: Message) -> None:
    """
    Handler to check the message ignoring the user nonspam status
    """
    if not (message.chat and message.from_user and (await message.chat.get_member(message.from_user.id) in await message.chat.get_administrators())):
        return
    logging.info("Handling check for admin %s(%s)", message.from_user.full_name, message.from_user.id)
    if message.reply_to_message and message.reply_to_message.text:
        is_spam = predictor.predict(message.reply_to_message.text)
        if is_spam:
            await message.reply_to_message.delete()
            await message.answer(
                "Спам удален🥰",
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
                        "User %s(%s) has no non-spam messages, deleting spam message",
                        message.from_user.full_name,
                        message.from_user.id,
                    )
                    await message.delete()


async def main() -> None:
    await init_tables()

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
