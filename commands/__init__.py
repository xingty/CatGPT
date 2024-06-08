import asyncio
import importlib
from pathlib import Path

from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand
from telebot.asyncio_helper import RequestTimeout

from context import session, profiles, config
from utils.md2tgmd import escape
from utils.text import messages_to_segments
from utils.prompt import get_prompt
from share.github import create_or_update_issue


async def send_message(
        bot: AsyncTeleBot,
        chat_id: int,
        reply_id: int,
        text: str,
        parse_mode: str = "MarkdownV2",
        disable_preview: bool = True
):
    retry_counter = 0
    while retry_counter < 3:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=escape(text),
                reply_to_message_id=reply_id,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
            break
        except RequestTimeout as e:
            timeout = retry_counter * 1.5 + 3
            retry_counter += 1
            err_msg = f"Sending message timeout error: \n{text[0:10]}...\n{str(e)}\nRetrying after {timeout} seconds..."
            print(err_msg)
            await asyncio.sleep(timeout)


def permission_check(func):
    async def wrapper(message: Message, bot: AsyncTeleBot):
        uid = str(message.from_user.id)
        if session.is_enrolled(uid):
            await func(message, bot)
        else:
            text = "Please enter a valid key to use this bot. You can do this by typing '/key key'."
            await send_message(bot, message.chat.id, message.message_id, text)

    return wrapper


async def register_commands(bot: AsyncTeleBot) -> None:
    bot_commands = []
    action_provider = {}

    # import all submodules
    for name in all_commands():
        module = importlib.import_module(f".{name}", __package__)

        if hasattr(module, "register"):
            module.register(bot, permission_check)

        if hasattr(module, "action"):
            module_info = getattr(module, "action")
            bot_commands.append(BotCommand(module_info["name"], module_info["description"]))
            if "handler" in module_info:
                action_provider[module_info["name"]] = module_info
    await bot.set_my_commands(bot_commands)

    @bot.callback_query_handler(func=lambda call: True)
    async def callback_handler(call):
        message: Message = call.message
        segments = call.data.split(':')
        uid = str(call.from_user.id)
        target = segments[0]
        operation = segments[1]
        message_id = int(segments[2])
        chat_id = int(segments[3])
        source_uid = int(segments[4])

        if call.from_user.id != source_uid:
            return
        provider = action_provider.get(target)
        if provider is not None:
            handler = provider["handler"]
            await handler(
                bot=bot,
                operation=operation,
                msg_id=message_id,
                chat_id=chat_id,
                uid=uid,
                message=message,
            )

            delete = provider.get("delete_after_invoke", True)
            if delete:
                await bot.delete_message(message.chat.id, message.message_id)


def all_commands() -> list[str]:
    commands = []
    this_path = Path(__file__).parent
    for child in this_path.iterdir():
        if child.name.startswith("_"):
            continue
        commands.append(child.stem)
    return commands


async def show_conversation(chat_id: int, msg_id: int, uid: str, bot: AsyncTeleBot, convo: dict,
                            reply_msg_id: int = None):
    messages = convo.get("context", [])
    messages = [msg for msg in messages if (msg["role"] != "system" and msg["chat_id"] == chat_id)]
    segments = messages_to_segments(messages)
    if len(segments) == 0:
        await bot.send_message(
            chat_id=chat_id,
            text=escape(f"Current topic: **{convo['title']}**\n"),
            parse_mode="MarkdownV2",
        )
        return

    last_message_id = reply_msg_id
    context = f'{msg_id}:{chat_id}:{uid}'
    keyboard = [[
        InlineKeyboardButton("Share", callback_data=f'conversation:share_{convo["id"]}:{context}'),
        InlineKeyboardButton("Download", callback_data=f'conversation:dl_{convo["id"]}:{context}')
    ]]
    for content in segments:
        reply_msg: Message = await bot.send_message(
            chat_id=chat_id,
            text=escape(content),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_to_message_id=last_message_id,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        last_message_id = reply_msg.message_id


def create_convo_and_update_profile(uid: str, chat_id: int, profile: dict, title: str = None) -> dict:
    prompt = get_prompt(profile)
    messages = [prompt] if prompt else None
    convo = session.create_convo(uid, chat_id, title, messages)
    profile["conversation"][chat_id] = convo["id"]
    profiles.update_all(uid, profile)

    return convo


def get_profile_text(uid: str, chat_id: int):
    profile = profiles.load(uid)
    convo = session.get_convo(uid, profile["conversation"].get(str(chat_id))) or {}
    text = f"current topic: `{convo.get('title', 'None')}`\n"
    text = f"{text}model: `{profile['model']}`\nendpoint: `{profile['endpoint']}`\nprompt: `{profile['role']}`"

    return text


async def share(convo: dict):
    messages = convo.get("context", [])
    body = messages_to_segments(messages, 65535)[0]

    return await create_or_update_issue(
        owner=config.share_info.get("owner"),
        repo=config.share_info.get("repo"),
        token=config.share_info.get("token"),
        title=convo.get("title"),
        label=convo.get("label"),
        body=body,
    )
