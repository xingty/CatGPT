from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputFile

from utils.md2tgmd import escape
from utils.text import encode_message_id
from context import profiles, config, topic, get_bot_name
from . import show_conversation, share, send_file
from storage import types


async def handle_conversation(message: Message, bot: AsyncTeleBot):
    uid = message.from_user.id
    profile = await profiles.load(uid)
    convo_id = profile.get_conversation_id(message.chat.type)
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
            reply_msg_id=message.message_id
        )
        return

    if instruction == "share":
        await _do_share(convo, bot, message)
    elif instruction == "download":
        await send_file(bot, message, convo)
    else:
        convo.title = instruction
        convo.generate_title = False
        await profiles.update(uid, profile)
        await topic.update_topic(convo)
        await bot.send_message(
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
            parse_mode="MarkdownV2",
            text=escape(f"topic's title has been updated to `{instruction}`")
        )


async def handle_download(
        bot: AsyncTeleBot,
        operation: str,
        msg_ids: list[int],
        chat_id: int,
        uid: str,
        message: Message
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
        message: Message
):
    convo = await topic.get_topic(int(operation))
    message_id = msg_ids[0]
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            parse_mode="MarkdownV2",
            text=escape(f'topic not found')
        )
        return

    if not config.share_info:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            parse_mode="MarkdownV2",
            text=escape(f"Please set share info in config")
        )
        return

    encoded_msg_id = encode_message_id(msg_ids + [message.message_id])
    context = f'{encoded_msg_id}:{message.chat.id}:{uid}'
    buttons = [[
        InlineKeyboardButton("yes", callback_data=f'do_share:yes_{operation}:{context}'),
        InlineKeyboardButton("no", callback_data=f'do_share:no:{context}'),
    ]]

    await bot.send_message(
        chat_id=chat_id,
        reply_to_message_id=message_id,
        parse_mode="MarkdownV2",
        text=escape(f"Share this topic `<{convo.title}>` to github?"),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def do_share(
        bot: AsyncTeleBot,
        operation: str,
        msg_ids: list[int],
        chat_id: int,
        uid: str,
        message: Message
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
            disable_web_page_preview=False
        )
    except Exception as e:
        await bot.send_message(
            chat_id=message.chat.id,
            parse_mode="MarkdownV2",
            text=str(e),
            disable_web_page_preview=True
        )


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_conversation)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])

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
