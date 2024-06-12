from io import BytesIO

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputFile

from utils.md2tgmd import escape
from context import profiles, config, topic, get_bot_name
from utils.text import messages_to_segments
from . import show_conversation, share
from storage import types


async def send_file(bot: AsyncTeleBot, message: Message, convo: types.Topic):
    messages: list[types.Message] = convo.messages or []
    messages = [msg for msg in messages if (msg.role != "system" and msg.chat_id == message.chat.id)]
    segment = messages_to_segments(messages, 65536)[0]
    file_object = BytesIO(segment.encode("utf-8"))
    file_object.name = f"{convo.title}.md"
    file = InputFile(file_object)
    file.file_name = f"{convo.title}.md"
    await bot.send_document(
        chat_id=message.chat.id,
        document=file,
    )


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
        await do_share(convo, bot, message)
    elif instruction == "download":
        await send_file(bot, message, convo)
    else:
        convo.title = instruction
        convo.generate_title = False
        await profiles.update(uid, profile)
        await bot.send_message(
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
            parse_mode="MarkdownV2",
            text=escape(f"topic's title has been updated to `{instruction}`")
        )


async def handle_share_convo(
        bot: AsyncTeleBot,
        operation: str,
        msg_id: int,
        chat_id: int,
        uid: str,
        message: Message
):
    segments = operation.split('_')
    real_op = segments[0]
    print("=" * 30)

    if real_op == "no":
        await bot.delete_message(message.chat.id, message.message_id)
        return

    convo_id = segments[1]
    convo = await topic.get_topic(int(convo_id), fetch_messages=True)
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=msg_id,
            parse_mode="MarkdownV2",
            text=escape(f'topic not found')
        )
        return

    if real_op == "share":
        if not config.share_info:
            await bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=msg_id,
                parse_mode="MarkdownV2",
                text=escape(f"Please set share info in config")
            )
            return

        context = f'{message.message_id}:{message.chat.id}:{uid}'
        buttons = [[
            InlineKeyboardButton("yes", callback_data=f'{action["name"]}:yes_{convo_id}:{context}'),
            InlineKeyboardButton("no", callback_data=f'{action["name"]}:no_{convo_id}:{context}'),
        ]]

        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=msg_id,
            parse_mode="MarkdownV2",
            text=escape(f"Share this topic `<{convo.title}>` to github?"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif real_op == "dl":
        await send_file(bot, message, convo)
        await bot.delete_message(message.chat.id, message.message_id)
    elif real_op == "yes":
        await do_share(convo, bot, message)
        await bot.delete_message(message.chat.id, message.message_id)


async def do_share(convo: types.Topic, bot: AsyncTeleBot, message: Message):
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


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_conversation)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])


action = {
    "name": "topic",
    "description": "current topic: [title]",
    "handler": handle_share_convo,
    "delete_after_invoke": False
}
