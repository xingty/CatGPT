from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.md2tgmd import escape
from ..utils.text import messages_to_segments
from ..context import profiles, topic, get_bot_name, config, page_preview
from . import share, send_file, handle_share
from ..storage import types
from ..types import Preview

preview_mapping = {
    "iv": Preview.TELEGRAPH,
    "inner": Preview.INTERNAL,
}


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
    instruction = (
        message.text.replace("/topic", "").replace(bot_name, "").strip().lower()
    )
    if len(instruction) == 0 or instruction in ["inner", "iv"]:
        preview_type = preview_mapping.get(instruction, config.topic_preview)
        await show_conversation(
            chat_id=message.chat.id,
            msg_id=message.message_id,
            uid=uid,
            bot=bot,
            convo=convo,
            profile=profile,
            reply_msg_id=message.message_id,
            thread_id=message.message_thread_id,
            preview_type=preview_type,
        )
        return

    if instruction == "share":
        if len(convo.messages) == 0:
            await bot.send_message(
                chat_id=message.chat.id,
                parse_mode="MarkdownV2",
                text=escape("No messages found in this topic"),
                message_thread_id=message.message_thread_id,
            )
            return

        size = len(share.share_providers)
        if size == 0:
            await bot.send_message(
                chat_id=message.chat.id,
                parse_mode="MarkdownV2",
                text=escape(f"Please set share info in the config file"),
                message_thread_id=message.message_thread_id,
            )
        elif size == 1:
            provider_name = next(iter(share.share_providers))
            await do_share(
                bot=bot,
                operation=f"{provider_name}_{convo_id}",
                msg_ids=[message.message_id],
                chat_id=message.chat.id,
                uid=uid,
                message=message,
            )
        else:
            await handle_share(
                bot=bot,
                operation=str(convo_id),
                msg_ids=[message.message_id],
                chat_id=message.chat.id,
                uid=uid,
                message=message,
            )
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
    profile: types.Profile,
    reply_msg_id: int = None,
    thread_id: int = None,
    preview_type: Preview = None,
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
            InlineKeyboardButton("share", callback_data=f"share:{convo.tid}:{context}"),
            InlineKeyboardButton(
                "download", callback_data=f"download:{convo.tid}:{context}"
            ),
            InlineKeyboardButton("dismiss", callback_data=f"topic:dismiss:{context}"),
        ]
    ]

    if preview_type == Preview.TELEGRAPH:
        md_content = "\n\n".join(segments)
        html_url = await page_preview.preview_md_text(profile, convo.title, md_content)
        await bot.send_message(
            chat_id=chat_id,
            text=f"[{convo.title}]({html_url})",
            reply_to_message_id=last_message_id,
            disable_web_page_preview=False,
            reply_markup=InlineKeyboardMarkup(keyboard),
            message_thread_id=thread_id,
            parse_mode="MarkdownV2",
        )
    else:
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


async def do_share(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: int,
    message: Message,
):
    if operation == "dismiss":
        await bot.delete_message(chat_id, message.message_id)
        return

    segments = operation.split("_")
    provider = share.share_providers.get(segments[0])
    if not provider:
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f"Unknown share provider: {segments[0]}"),
            message_thread_id=message.message_thread_id,
        )
        await bot.delete_message(chat_id, message.message_id)
        return

    thread = await topic.get_topic(topic_id=int(segments[1]), fetch_messages=True)
    html_url = await provider.share(thread)

    await bot.send_message(
        chat_id=chat_id,
        text=html_url,
        message_thread_id=message.message_thread_id,
        disable_web_page_preview=False,
    )

    await bot.delete_messages(chat_id, msg_ids + [message.message_id])


async def handle_dismiss(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: str,
    message: Message,
):
    await bot.delete_messages(chat_id, msg_ids + [message.message_id])


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_conversation)
    bot.register_message_handler(handler, pass_bot=True, commands=[action["name"]])

    action_provider["share"] = handle_share
    action_provider["download"] = handle_download
    action_provider["do_share"] = do_share
    action_provider["topic"] = handle_dismiss

    return action


action = {
    "name": "topic",
    "description": "current topic: [share|download|inner|title]",
    "order": 30,
}
