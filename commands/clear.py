from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from context import session, profiles
from utils.md2tgmd import escape


async def handle_clear(message: Message, bot: AsyncTeleBot) -> None:
    context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f'clear:yes:{context}'),
            InlineKeyboardButton("No", callback_data=f'clear:no:{context}'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=message.chat.id,
        text='Chat history in current window will be cleared, are you sure?',
        reply_markup=reply_markup
    )


async def do_clear(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: str, message: Message) -> None:
    if operation != "yes":
        await bot.delete_message(chat_id, msg_id)
        return

    profile = profiles.load(uid)
    convo_id = profile.get("conversation_id")
    convo = session.get_convo(uid, convo_id)
    if convo is None:
        return

    messages = convo.get("context", [])
    messages = [msg for msg in messages if (msg["role"] == "system" or msg["chat_id"] != chat_id)]
    convo["context"] = messages

    session.save_convo(uid, convo)

    await bot.send_message(
        chat_id=chat_id,
        text=escape("`Context cleared.`"),
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2"
    )
    await bot.delete_message(chat_id, msg_id)


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_clear)
    bot.register_message_handler(handler, pass_bot=True, commands=['clear'])


action = {
    "name": 'clear',
    "description": 'Clear context',
    "handler": do_clear,
}

