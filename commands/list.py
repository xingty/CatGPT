from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from utils.md2tgmd import escape
from context import profiles, session


async def handle_convo(message: Message, bot: AsyncTeleBot):
    uid = str(message.from_user.id)
    profile = profiles.load(uid)
    current_convo = session.get_convo(uid, profile.get("conversation_id"))
    context = f'{message.message_id}:{message.chat.id}:{uid}'
    keyboard = []
    items = []

    title = current_convo.get('title', 'None')
    text = f"Current conversation: `{title}` \n\nConversation list:\n"
    conversations = session.list_conversation(uid)
    for index, convo in enumerate(conversations):
        seq = str(index+1)
        callback_data = f'{action["name"]}:{convo["id"]}:{context}'
        if len(items) == 4:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(seq, callback_data=callback_data))
        text += f"{seq}. {convo['title']}\n"

    if len(items) > 0:
        keyboard.append(items)

    await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def do_convo_change(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: str, message: Message):
    convo = session.get_convo(uid, operation)
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=msg_id,
            parse_mode="MarkdownV2",
            text=escape(f'conversation `{operation}` not found')
        )
        return

    profile = profiles.load(uid)
    if profile.get("conversation_id") != operation:
        profile["conversation_id"] = operation
        profiles.update_all(uid, profile)

    await bot.send_message(
        chat_id=chat_id,
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2",
        text=escape(f'current conversation: `{convo["title"]}`')
    )


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_convo)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])


action = {
    "name": 'convo',
    "description": 'all conversations',
    "handler": do_convo_change,
    "delete_after_invoke": False
}
