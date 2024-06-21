from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.md2tgmd import escape
from ..utils.text import encode_message_id, messages_to_segments
from ..context import profiles, config, topic, get_bot_name
from . import share, send_file
from ..storage import types


async def handle_conversation(message: Message, bot: AsyncTeleBot):
    uid = message.from_user.id
    profile = await profiles.load(uid, message.chat.id, message.message_thread_id)
    convo_id = profile.topic_id
    convo = await topic.get_topic(convo_id, fetch_messages=True)
    if convo is None:
        text = "Topic not found. Please start a new topic or switch to a existing one."
        await bot.reply_to(message, text)
        return

    bot_name = await get_bot_name()
    instruction = message.text.replace("/topic", "").replace(bot_name, "").strip()
    if len(instruction) == 0:
        await show_conversation(
            chat_id=message.chat.id,
            msg_id=message.message_id,
            uid=uid,
            bot=bot,
            convo=convo,
            reply_msg_id=message.message_id,
            thread_id=message.message_thread_id,
        )
        return

    if instruction == "share":
        await _do_share(convo, bot, message)
    elif instruction == "download":
        await send_file(bot, message, convo)
    else:
        convo.title = instruction
        convo.generate_title = False
        await profiles.update(uid, message.chat.id, message.message_thread_id, profile)
        await topic.update_topic(convo)
        await bot.send_message(
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
            parse_mode="MarkdownV2",
            text=escape(f"topic's title has been updated to `{instruction}`"),
            message_thread_id=message.message_thread_id,
        )


async def show_conversation(
    chat_id: int,
    msg_id: int,
    uid: int,
    bot: AsyncTeleBot,
    convo: types.Topic,
    reply_msg_id: int = None,
    thread_id: int = None,
):
    messages: list[types.Message] = convo.messages or []
    messages = [
        msg for msg in messages if (msg.role != "system" and msg.chat_id == chat_id)
    ]
    segments = messages_to_segments(messages)
    if len(segments) == 0:
        await bot.send_message(
            chat_id=chat_id,
            text=escape(f"Current topic: **{convo.title}**\n"),
            parse_mode="MarkdownV2",
            message_thread_id=thread_id,
        )
        return

    last_message_id = reply_msg_id
    context = f"{msg_id}:{chat_id}:{uid}"
    keyboard = [
        [
            InlineKeyboardButton("Share", callback_data=f"share:{convo.tid}:{context}"),
            InlineKeyboardButton(
                "Download", callback_data=f"download:{convo.tid}:{context}"
            ),
        ]
    ]
    for content in segments:
        reply_msg: Message = await bot.send_message(
            chat_id=chat_id,
            text=escape(content),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_to_message_id=last_message_id,
            reply_markup=InlineKeyboardMarkup(keyboard),
            message_thread_id=thread_id,
        )
        last_message_id = reply_msg.message_id


async def handle_download(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: str,
    message: Message,
):
    convo = await topic.get_topic(int(operation), fetch_messages=True)
    await send_file(bot, message, convo)
    await bot.delete_messages(message.chat.id, msg_ids + [message.message_id])


async def handle_share(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: str,
    message: Message,
):
    convo = await topic.get_topic(int(operation))
    message_id = msg_ids[0]
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            parse_mode="MarkdownV2",
            text=escape(f"topic not found"),
            message_thread_id=message.message_thread_id,
        )
        return

    if not config.share_info:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            parse_mode="MarkdownV2",
            text=escape(f"Please set share info in config"),
            message_thread_id=message.message_thread_id,
        )
        return

    encoded_msg_id = encode_message_id(msg_ids + [message.message_id])
    context = f"{encoded_msg_id}:{message.chat.id}:{uid}"
    buttons = [
        [
            InlineKeyboardButton(
                "yes", callback_data=f"do_share:yes_{operation}:{context}"
            ),
            InlineKeyboardButton("no", callback_data=f"do_share:no:{context}"),
        ]
    ]

    await bot.send_message(
        chat_id=chat_id,
        reply_to_message_id=message_id,
        parse_mode="MarkdownV2",
        text=escape(f"Share this topic `<{convo.title}>` to github?"),
        reply_markup=InlineKeyboardMarkup(buttons),
        message_thread_id=message.message_thread_id,
    )


async def do_share(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: str,
    message: Message,
):
    if operation == "no":
        await bot.delete_message(chat_id, message.message_id)
    else:
        convo_id = int(operation.split("_")[1])
        convo = await topic.get_topic(convo_id, fetch_messages=True)
        await _do_share(convo, bot, message)
        await bot.delete_messages(chat_id, msg_ids + [message.message_id])


async def _do_share(convo: types.Topic, bot: AsyncTeleBot, message: Message):
    html_url = await share(convo)
    try:
        await bot.send_message(
            chat_id=message.chat.id,
            parse_mode="MarkdownV2",
            text=escape(f"Title: {convo.title}\nShare link: {html_url}"),
            disable_web_page_preview=False,
            message_thread_id=message.message_thread_id,
        )
    except Exception as e:
        await bot.send_message(
            chat_id=message.chat.id,
            parse_mode="MarkdownV2",
            text=str(e),
            disable_web_page_preview=True,
            message_thread_id=message.message_thread_id,
        )


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_conversation)
    bot.register_message_handler(handler, pass_bot=True, commands=[action["name"]])

    action_provider["share"] = handle_share
    action_provider["download"] = handle_download
    action_provider["do_share"] = do_share

    return action


action = {
    "name": "topic",
    "description": "current topic: [share|download|title]",
    "delete_after_invoke": False,
    "order": 30,
}
