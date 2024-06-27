import hashlib
import hmac

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from ..context import users, config


def compare(key1: str, key2: str):
    return hmac.compare_digest(key1.encode("utf-8"), key2.encode("utf-8"))


async def handle_key(message: Message, bot: AsyncTeleBot):
    uid = message.from_user.id
    if await users.is_enrolled(uid):
        msg = "You have already been registered in the system. No need to enter the key again."
    elif compare(message.text.replace("/key", "").strip(), config.access_key):
        await users.create_user(uid=uid, blocked=0)
        username = message.from_user.username
        msg = f'@{username} Your registration is complete. Have fun!"'
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    else:
        msg = "Invalid key. Please enter a valid key to proceed."

    await bot.send_message(
        chat_id=message.chat.id, text=msg, message_thread_id=message.message_thread_id
    )


def register(bot: AsyncTeleBot, decorator, provider) -> None:
    bot.register_message_handler(
        handle_key, regexp=r"/key ", pass_bot=True, content_types=["text"]
    )
