# antispam-bot

AI Telegram bot for managing spam in big open telegram groups.

## Functionality

Uses [model](https://huggingface.co/RUSpam/spam_deberta_v4), based on the bert to detect spam messages.

If the user has already written any non-spam messages in the chat, ignores the message. Otherwise, deletes it.

**/check** command ignores the non-spam status and deletes the message you have replied to with the command as well as temporarily(til the next non-spam message) removing the deleting protection from the user, if it detects message was actually spam. Only avaliable to chat admins.

## Installation

- Obtain poetry
- Install dependencies:

```bash
poetry install
```

## Run

- Obtain the bot API key via @BotFather
- Run the bot providing the telegram API key:

```bash
BOT_TOKEN="YOUR_BOT_TOKEN" poetry run python src/bot.py
```
