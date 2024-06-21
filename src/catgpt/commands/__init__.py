import asyncio
import importlib
import logging
from pathlib import Path
from io import BytesIO

from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand
from telebot.asyncio_helper import RequestTimeout

from ..context import profiles, config, topic, users
from ..utils.md2tgmd import escape
from ..utils.text import messages_to_segments, decode_message_id
from ..utils.prompt import get_prompt
from ..share.github import create_or_update_issue
from ..storage import types, tx
from ..types import ChatType


async def send_message(
        bot: AsyncTeleBot,
        chat_id: int,
        reply_id: int,
        text: str,
        thread_id: int = None,
        parse_mode: str = "MarkdownV2",
        disable_preview: bool = True,
):
    retry_counter = 0
    while retry_counter < 3:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=escape(text),
                reply_to_message_id=reply_id,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
                message_thread_id=thread_id
            )
            break
        except RequestTimeout as e:
            timeout = retry_counter * 1.5 + 3
            retry_counter += 1
            err_msg = f"Sending message timeout error: \n{text[0:10]}...\n{str(e)}\nRetrying after {timeout} seconds..."
            print(err_msg)
            await asyncio.sleep(timeout)


async def new_profile(message: Message):
    endpoint = config.get_default_endpoint()
    uid = message.from_user.id

    t = await topic.new_topic(
        title="New Topic",
        chat_id=message.chat.id,
        user_id=uid,
        messages=[],
        generate_title=True,
        thread_id=message.message_thread_id
    )

    await profiles.create(
        uid=uid,
        endpoint=endpoint.name,
        model=endpoint.default_model,
        prompt="System",
        chat_id=message.chat.id,
        chat_type=ChatType.get(message.chat.type).value,
        thread_id=message.message_thread_id,
        topic_id=t.tid
    )


def permission_check(func):
    async def wrapper(message: Message, bot: AsyncTeleBot):
        try:
            uid = message.from_user.id
            if await users.is_enrolled(uid):
                if not await profiles.has_profile(uid, message.chat.id, message.message_thread_id):
                    await new_profile(message)

                await func(message, bot)
            else:
                text = "Please enter a valid key to use this bot. You can do this by typing '/key key'."
                await send_message(bot, message.chat.id, message.message_id, text, message.message_thread_id)
        except Exception as e:
            logging.exception(e)

    return wrapper


async def register_commands(bot: AsyncTeleBot) -> None:
    list_module_info = []
    action_provider = {}

    # import all submodules
    for name in all_modules():
        module = importlib.import_module(f".{name}", __package__)

        if hasattr(module, "register"):
            module_info = module.register(bot, permission_check, action_provider)
            if module_info:
                list_module_info.append(module_info)

    sorted_list = sorted(list_module_info, key=lambda x: x.get("order", 1000))
    bot_commands = [BotCommand(x["name"], x["description"]) for x in sorted_list]
    await bot.set_my_commands(bot_commands)

    @bot.callback_query_handler(func=lambda call: True)
    async def callback_handler(call):
        message: Message = call.message
        segments = call.data.split(":")
        uid = call.from_user.id
        target = segments[0]
        operation = segments[1]
        message_ids = decode_message_id(segments[2])
        chat_id = int(segments[3])
        source_uid = int(segments[4])

        if call.from_user.id != source_uid:
            return
        handler = action_provider.get(target)
        if handler is not None:
            try:
                await handler(
                    bot=bot,
                    operation=operation,
                    msg_ids=message_ids,
                    chat_id=chat_id,
                    uid=uid,
                    message=message,
                )
            except Exception as e:
                logging.exception(e)


def all_modules() -> list[str]:
    commands = []
    this_path = Path(__file__).parent
    for child in this_path.iterdir():
        if child.name.startswith("_"):
            continue
        commands.append(child.stem)
    return commands


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
            message_thread_id=thread_id
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
            message_thread_id=thread_id
        )
        last_message_id = reply_msg.message_id


async def create_convo_and_update_profile(
        uid: int,
        chat_id: int,
        profile: types.Profile,
        chat_type: str,
        title: str = None,
        thread_id: int = 0,
) -> types.Topic:
    prompt = get_prompt(profiles.get_prompt(profile.prompt))
    messages = [prompt] if prompt else None

    convo = await topic.new_topic(
        title=title,
        chat_id=chat_id,
        user_id=uid,
        messages=messages,
        generate_title=title is None or len(title) == 0,
        thread_id=thread_id,
    )

    profile.topic_id = convo.tid
    await profiles.update(uid, chat_id, thread_id, profile)

    return convo


async def get_profile_text(profile: types.Profile, chat_type: str):
    convo_title = "None"
    convo_id = profile.topic_id
    if convo_id:
        convo = await topic.get_topic(convo_id)
        if convo:
            convo_title = convo.title

    text = f"current topic: `{convo_title}`\n"
    text = f"{text}model: `{profile.model}`\nendpoint: `{profile.endpoint}`\nprompt: `{profile.prompt}`"

    return text


async def share(convo: types.Topic):
    messages = convo.messages
    body = messages_to_segments(messages, 65535)[0]

    return await create_or_update_issue(
        owner=config.share_info.get("owner"),
        repo=config.share_info.get("repo"),
        token=config.share_info.get("token"),
        title=convo.title,
        label=convo.label,
        body=body,
    )


async def send_file(bot: AsyncTeleBot, message: Message, convo: types.Topic):
    if len(convo.messages) == 0:
        return

    messages: list[types.Message] = convo.messages or []
    messages = [
        msg
        for msg in messages
        if (msg.role != "system" and msg.chat_id == message.chat.id)
    ]
    segment = messages_to_segments(messages, 65536)[0]
    file_object = BytesIO(segment.encode("utf-8"))
    file_object.name = f"{convo.title}.md"
    file = InputFile(file_object)
    file.file_name = f"{convo.title}.md"
    await bot.send_document(
        chat_id=message.chat.id,
        document=file,
        message_thread_id=message.message_thread_id
    )
