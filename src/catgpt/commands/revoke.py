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


async def handle_revoke(message: Message, bot: AsyncTeleBot):
    uid = message.from_user.id
    convo = await get_convo(uid, message.chat.id, message.message_thread_id)
    if convo is None:
        await bot.reply_to(message, "Please select a topic to use.")
        return

    messages: list[types.Message] = convo.messages or []
    revoke_messages = []
    for m in reversed(messages):
        if m.chat_id == message.chat.id:
            revoke_messages.insert(0, m)
        if len(revoke_messages) == 2:
            break

    if len(revoke_messages) != 2:
        await bot.reply_to(
            message, "Could not find any message.py in current conversation"
        )
        return

    context = f"{message.message_id}:{message.chat.id}:{message.from_user.id}"
    keyboard = [
        [
            InlineKeyboardButton(
                "Yes", callback_data=f'{action["name"]}:yes:{context}'
            ),
            InlineKeyboardButton("No", callback_data=f'{action["name"]}:no:{context}'),
        ],
    ]

    content = ""
    for m in revoke_messages:
        content += f"### {m.role}\n{m.content}\n\n"

    content = escape(
        f"Are you sure? This operation will revoke the messages below:\n\n{content}"
    )
    if len(content) > 4096:
        content = content[0:4093] + "..."

    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(content),
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

    messages: list[types.Message] = convo.messages or []
    revoke_message_ids = []
    i = len(messages) - 1
    while i >= 0 and len(revoke_message_ids) < 2:
        if messages[i].chat_id == chat_id:
            revoke_message_ids.append(messages.pop(i).message_id)
        i -= 1

    if len(revoke_message_ids) != 2:
        await bot.send_message(
            chat_id=chat_id,
            text="Could not find any message.py in current conversation",
            reply_to_message_id=message_id,
            message_thread_id=message.message_thread_id,
        )
        return

    await topic.remove_messages(convo.tid, revoke_message_ids)
    revoke_message_ids.append(message.message_id)
    await bot.delete_messages(chat_id, revoke_message_ids)

    await bot.send_message(
        chat_id=chat_id,
        text="Messages revoked",
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
