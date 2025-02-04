from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ..context import profiles, topic
from ..utils.md2tgmd import escape
from ..storage import types


async def get_convo(uid, chat_id, thread_id) -> types.Topic:
    profile = await profiles.load(uid, chat_id, thread_id)
    convo_id = profile.topic_id
    convo = await topic.get_topic(convo_id, fetch_messages=True)

    return convo


async def get_messages_to_revoke(messages: list[types.Message], chat_id: int, count: int = None) -> list[types.Message]:
    """Get messages to revoke based on count or until last user message"""
    result = []
    
    for msg in reversed(messages):
        if msg.chat_id != chat_id:
            continue
            
        result.insert(0, msg)
        
        # If count specified, just take that many messages
        if count is not None:
            if len(result) >= count:
                break
        # If no count, take messages until we find a user message
        elif msg.role == "user":
            break
            
    return result


async def handle_revoke(message: Message, bot: AsyncTeleBot):
    uid = message.from_user.id
    convo = await get_convo(uid, message.chat.id, message.message_thread_id)
    if convo is None:
        await bot.reply_to(message, "Please select a topic to use.")
        return

    # Parse count from command if provided
    try:
        count = int(message.text.split()[1]) if len(message.text.split()) > 1 else None
    except ValueError:
        count = None

    messages: list[types.Message] = convo.messages or []
    revoke_messages = await get_messages_to_revoke(messages, message.chat.id, count)

    if not revoke_messages:
        await bot.reply_to(message, "Could not find any messages in current conversation")
        return

    context = f"{message.message_id}:{message.chat.id}:{message.from_user.id}"
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f'{action["name"]}:yes:{context}'),
            InlineKeyboardButton("No", callback_data=f'{action["name"]}:no:{context}'),
        ],
    ]

    content = ""
    for m in revoke_messages:
        content += f"### {m.role}\n{m.content}\n\n"

    content = escape(f"Are you sure? This operation will revoke the messages below:\n\n{content}")
    if len(content) > 4096:
        content = content[0:4095]

    await bot.send_message(
        chat_id=message.chat.id,
        text=content,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
        message_thread_id=message.message_thread_id,
    )


async def do_revoke(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: int,
    message: Message,
):
    message_id = msg_ids[0]
    if operation == "no":
        await bot.delete_messages(chat_id, [message_id, message.message_id])
        return

    convo = await get_convo(uid, chat_id, message.message_thread_id)
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            text="Conversation not found",
            reply_to_message_id=message_id,
            message_thread_id=message.message_thread_id,
        )
        return

    # Try to get count from original revoke command
    try:
        orig_msg = await bot.get_message(chat_id, message_id)
        count = int(orig_msg.text.split()[1]) if len(orig_msg.text.split()) > 1 else None
    except (ValueError, AttributeError):
        count = None

    messages: list[types.Message] = convo.messages or []
    revoke_messages = await get_messages_to_revoke(messages, chat_id, count)
    
    if not revoke_messages:
        await bot.send_message(
            chat_id=chat_id,
            text="Could not find any messages in the current conversation",
            reply_to_message_id=message_id,
            message_thread_id=message.message_thread_id,
        )
        return

    # Remove messages from conversation
    message_ids = [m.message_id for m in revoke_messages]
    await topic.remove_messages(convo.tid, message_ids)
    
    # Delete messages from chat
    message_ids.append(message.message_id)
    await bot.delete_messages(chat_id, message_ids)

    await bot.send_message(
        chat_id=chat_id,
        text=f"{len(message_ids)-1} messages revoked",
        reply_to_message_id=message_id,
        message_thread_id=message.message_thread_id,
    )


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_revoke)
    bot.register_message_handler(handler, pass_bot=True, commands=[action["name"]])

    action_provider[action["name"]] = do_revoke

    return action


action = {
    "name": "revoke",
    "description": "revoke message.py",
    "order": 70,
}
