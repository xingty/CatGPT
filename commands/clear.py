from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from context import session, profiles, get_bot_name
from utils.md2tgmd import escape
from utils.prompt import get_prompt

DELETE_INSTRUCTIONS = ["delete", "all"]


async def handle_clear(message: Message, bot: AsyncTeleBot) -> None:
    bot_name = await get_bot_name()
    text = message.text.replace("/clear", "").replace(bot_name, "").strip()
    if len(text) > 0 and text in DELETE_INSTRUCTIONS:
        uid = str(message.from_user.id)
        await do_clear(bot, text, message.message_id, message.chat.id, uid, message)
        return

    context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
    keyboard = [
        [
            InlineKeyboardButton("delete", callback_data=f'{action["name"]}:yes:{context}'),
            InlineKeyboardButton("delete all", callback_data=f'{action["name"]}:all:{context}'),
            InlineKeyboardButton("dismiss", callback_data=f'{action["name"]}:no:{context}'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=message.chat.id,
        text='Chat history in current window will be cleared, are you sure?',
        reply_markup=reply_markup
    )


async def do_clear(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: str, message: Message) -> None:
    if operation == "no":
        await bot.delete_message(chat_id, msg_id)
        return

    profile = profiles.load(uid)
    convo_id = profile["conversation"].get(str(chat_id))
    convo = session.get_convo(uid, convo_id)
    if convo is None:
        return

    messages = convo.get("context", [])
    message_ids = [msg["message_id"] for msg in messages if msg["role"] != "system"]
    prompt = get_prompt(profile)
    new_message = [prompt] if prompt else []

    convo["context"] = new_message
    convo["generate_title"] = True
    convo["title"] = "new topic"

    session.save_convo(uid, convo)

    await bot.send_message(
        chat_id=chat_id,
        text=escape("`Context cleared.`"),
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2"
    )
    await bot.delete_message(chat_id, msg_id)

    if len(message_ids) > 0 and operation == "all":
        try:
            await bot.delete_messages(chat_id, message_ids)
        except Exception as e:
            print(e)


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_clear)
    bot.register_message_handler(handler, pass_bot=True, commands=['clear'])


action = {
    "name": 'clear',
    "description": 'clear context: [delete|all]',
    "handler": do_clear,
}

