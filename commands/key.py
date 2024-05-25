from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
from context import session, profiles, config
from utils.prompt import get_system_prompt
import hmac


def enroll(uid):
    endpoint = config.get_default_endpoint()
    prompt = get_system_prompt(endpoint["default_model"])
    prompts = []
    if prompt is not None:
        prompts.append({
            "role": "system",
            "content": prompt
        })

    convo_list = session.enroll(uid, prompts)

    profile = {
        "conversation_id": convo_list[0].get("id"),
        "model": endpoint["default_model"],
        "endpoint": endpoint["name"],
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
    elif compare(message.text.replace('/key ', ''), config.access_key):
        enroll(uid)
        msg = 'successful!'
    else:
        msg = 'Invalid key. Please enter a valid key to proceed.'

    await bot.reply_to(message, msg)


def register(bot: AsyncTeleBot, decorator) -> None:
    bot.register_message_handler(handle_key, regexp=r"/key ", pass_bot=True, content_types=["text"])

