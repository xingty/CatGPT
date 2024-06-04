from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
from context import session, profiles, get_bot_name
from utils.md2tgmd import escape
from utils.prompt import get_prompt
from . import get_profile_text


async def handle_new_topic(message: Message, bot: AsyncTeleBot) -> None:
    bot_name = await get_bot_name()
    text = message.text.replace('/new', '').replace(bot_name, "").strip()
    uid = str(message.from_user.id)
    await create_convo(bot, message.message_id, message.chat.id, uid, text)


async def create_convo(bot: AsyncTeleBot, msg_id: int, chat_id: int, uid: str, title: str = None) -> None:
    profile = profiles.load(uid)
    prompt = get_prompt(profile)
    messages = [prompt] if prompt else None
    convo = session.create_convo(uid, chat_id, title, messages)
    profile["conversation"][str(chat_id)] = convo.get("id")
    profiles.update_all(uid, profile)

    text = get_profile_text(uid, chat_id)
    text = "A new topic has been created.\n" + text

    await bot.send_message(
        chat_id=chat_id,
        text=escape(text),
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2"
    )


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_new_topic)
    bot.register_message_handler(handler, pass_bot=True, commands=['new'])


action = {
    "name": 'new',
    "description": 'start a new topic: [title]',
    # "handler": do_create_topic,
}
