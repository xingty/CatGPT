import json

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from utils.md2tgmd import escape
from context import session, profiles, config


def get_convo(uid: str):
    profile = profiles.load(uid)
    convo_id = profile.get("conversation_id")
    convo = session.get_convo(uid, convo_id)

    return convo


async def handle_revoke(message: Message, bot: AsyncTeleBot):
    uid = str(message.from_user.id)
    convo = get_convo(uid)
    if convo is None:
        await bot.reply_to(message, "Please select a conversation to use.")
        return

    messages = convo.get("context", [])
    revoke_messages = []
    for m in reversed(messages):
        if m.get("chat_id") == message.chat.id:
            revoke_messages.insert(0, m)
        if len(revoke_messages) == 2:
            break

    if len(revoke_messages) != 2:
        await bot.reply_to(message, "Could not find any message in current conversation")
        return

    context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f'{action["name"]}:yes:{context}'),
            InlineKeyboardButton("No", callback_data=f'{action["name"]}:no:{context}'),
        ],
    ]

    content = ''
    for m in revoke_messages:
        content += f'### {m["role"]}\n{m["content"]}\n\n'

    content = f'Are you sure? This operation will revoke the messages below:\n\n{content}'

    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(content),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def do_revoke(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: str, message: Message):
    if operation != 'yes':
        await bot.delete_message(chat_id, msg_id)
        return

    convo = get_convo(uid)
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            text="Conversation not found",
            reply_to_message_id=msg_id
        )
        return

    messages = convo.get("context", [])
    revoke_messages = []
    i = len(messages) - 1
    while i >= 0 and len(revoke_messages) < 2:
        if messages[i].get("chat_id") == chat_id:
            revoke_messages.append(messages.pop(i))
        i -= 1

    if len(revoke_messages) != 2:
        await bot.send_message(
            chat_id=chat_id,
            text="Could not find any message in current conversation",
            reply_to_message_id=msg_id
        )
        return

    content = ''
    for m in revoke_messages:
        content += f'### {m["role"]}\n{m["content"]}\n\n'

    await bot.send_message(
        chat_id=chat_id,
        text=escape(content),
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2"
    )
    session.sync_convo(uid)
    for m in revoke_messages:
        if 'message_id' in m and 'chat_id' in m:
            await bot.delete_message(m['chat_id'], m['message_id'])


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_revoke)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])


action = {
    "name": 'revoke',
    "description": 'revoke message',
    "handler": do_revoke,
}
