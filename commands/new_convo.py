from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from context import session, profiles
from utils.md2tgmd import escape
from utils.prompt import get_prompt


async def handle_new_topic(message: Message, bot: AsyncTeleBot) -> None:
    text = message.text.replace('/new', '').strip()
    uid = str(message.from_user.id)
    await create_convo(bot, message.message_id, message.chat.id, uid, text)


async def create_convo(bot: AsyncTeleBot, msg_id: int, chat_id: int, uid: str, title: str = None) -> None:
    profile = profiles.load(uid)
    prompt = get_prompt(profile)
    messages = [prompt] if prompt else None
    convo = session.create_convo(uid, chat_id, title, messages)
    profile["conversation_id"] = convo.get("id")
    profiles.update_all(uid, profile)

    text = (
        "A new topic has been created.\nCurrent conversation: `{title}`\nPrompt: `{prompt}`\nendpoint: `{""endpoint}` \nmodel: `{model}`".
        format(
            title=convo.get('title'),
            prompt=profile.get('role'),
            endpoint=profile.get('endpoint'),
            model=profile.get('model')
        ))

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
    "description": 'start a new conversation',
    # "handler": do_create_topic,
}
