from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
from context import session, profiles, config
import hmac


def enroll(uid):
    endpoint = config.get_default_endpoint()
    session.enroll(uid)

    profile = {
        "conversation": {},
        "model": endpoint.default_model,
        "endpoint": endpoint.name,
        "role": "System",
        "prompt": None
    }

    profiles.update_all(uid, profile)


def compare(key1: str, key2: str):
    return hmac.compare_digest(key1.encode('utf-8'), key2.encode('utf-8'))


async def handle_key(message: Message, bot: AsyncTeleBot):
    uid = str(message.from_user.id)
    if session.is_enrolled(uid):
        msg = 'You have already been registered in the system. No need to enter the key again.'
    elif compare(message.text.replace('/key', '').strip(), config.access_key):
        enroll(uid)
        username = message.from_user.username
        msg = f'@{username} Your registration is complete. Have fun!"'
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    else:
        msg = 'Invalid key. Please enter a valid key to proceed.'

    await bot.send_message(
        chat_id=message.chat.id,
        text=msg
    )


def register(bot: AsyncTeleBot, decorator) -> None:
    bot.register_message_handler(handle_key, regexp=r"/key ", pass_bot=True, content_types=["text"])

