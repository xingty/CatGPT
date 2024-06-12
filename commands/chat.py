from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message

from context import profiles, config, get_bot_name, topic
from context import Endpoint
from utils.text import get_timeout_from_text, MAX_TEXT_LENGTH
from . import create_convo_and_update_profile
from ask import ask_stream, ask
from utils.md2tgmd import escape
from storage import types

import time
import asyncio


async def is_mention_me(message: Message) -> bool:
    if message.entities is None:
        return False

    bot_name = await get_bot_name()
    text = message.text
    for entity in message.entities:
        if entity.type == "mention":
            who = text[entity.offset:entity.offset + entity.length]
            if who == bot_name:
                return True

    return False


async def send_message(bot: AsyncTeleBot, message: Message, text: str):
    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(text),
        reply_to_message_id=message.message_id
    )


async def handle_message(message: Message, bot: AsyncTeleBot) -> None:
    message_text = message.text
    if message.chat.type in ["group", "supergroup", "gigagroup", "channel"]:
        bot_name = await get_bot_name()
        message_text = message_text.replace(bot_name, "").strip()

    uid = message.from_user.id
    chat_id = message.chat.id
    profile = await profiles.load(uid)
    convo_id = profile.get_conversation_id(message.chat.type)

    convo = await topic.get_topic(convo_id, fetch_messages=True)
    if convo is None:
        convo = await create_convo_and_update_profile(
            uid=uid,
            chat_id=chat_id,
            profile=profile,
            chat_type=message.chat.type,
        )

    endpoint: Endpoint = config.get_endpoint(profile.endpoint)
    if endpoint is None:
        await bot.reply_to(
            message=message,
            text="Please select an endpoint to use."
        )
        return

    # messages = convo.messages
    messages_payload = [{"role": m.role, "content": m.content} for m in convo.messages]
    messages_payload.append({
        "role": "user",
        "content": message_text
    })
    print(messages_payload)
    model = profile.model
    if model not in endpoint.models:
        model = endpoint.default_model

    reply_msg = await bot.reply_to(
        message=message,
        text="A smart cat is thinking..."
    )

    try:
        text = await do_reply(endpoint, model, messages_payload, reply_msg, bot)
        message.text = message_text
        reply_msg.text = text
        await topic.append_messages(convo_id, message, reply_msg)

        try:
            generate_title = convo.generate_title
            if generate_title:
                await do_generate_title(convo, messages_payload, uid, text)
        except Exception as ie:
            print(ie)
    except Exception as e:
        await bot.send_message(
            chat_id=message.chat.id,
            reply_to_message_id=reply_msg.message_id,
            text=f"Error: {e}"
        )
        return


async def do_reply(endpoint: Endpoint, model: str, messages: list, reply_msg: Message, bot: AsyncTeleBot):
    text = ""
    buffered = ""
    start = time.time()
    timeout = 1.8
    text_overflow = False
    async for chunk in ask_stream(endpoint, {
        "model": model,
        "messages": messages,
    }):
        content = chunk["content"]
        buffered += content if content is not None else ""
        finished = chunk["finished"] == "stop"

        if text_overflow:
            continue

        if (time.time() - start > timeout and len(buffered) >= 18) or finished:
            start = time.time()
            try:
                message_text = escape(text + buffered)
                if len(message_text) > MAX_TEXT_LENGTH:
                    text_overflow = True
                    continue

                await bot.edit_message_text(
                    text=message_text,
                    chat_id=reply_msg.chat.id,
                    message_id=reply_msg.message_id,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True
                )
                text += buffered
                buffered = ""
                timeout = 1.8
            except ApiTelegramException as ae:
                print(ae)
                if ae.error_code == 400:
                    timeout = 2.5
                    print(escape(text + buffered))
                elif ae.error_code != 429:
                    seconds = get_timeout_from_text(ae.description)
                    timeout = 10 if seconds < 0 else seconds + 1
                else:
                    raise ae

    if len(buffered) > 0:
        delta = timeout - (time.time() - start)
        if delta > 0:
            await asyncio.sleep(int(delta) + 1)

        text += buffered
        msg_text = escape(text)
        if text_overflow or len(msg_text) > MAX_TEXT_LENGTH:
            text_overflow = True
            msg_text = escape(text)

        msg = await bot.edit_message_text(
            text=msg_text,
            chat_id=reply_msg.chat.id,
            message_id=reply_msg.message_id,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )

        if text_overflow:
            await bot.send_message(
                chat_id=reply_msg.chat.id,
                text=escape(buffered),
                reply_to_message_id=msg.message_id
            )

    return text


async def do_generate_title(convo: types.Topic, messages: list, uid: int, text: str):
    endpoint = config.get_title_endpoint()[0]
    if endpoint is None:
        return

    messages += [
        {
            "role": "assistant",
            "content": text
        },
        {
            "role": "user",
            "content": "Please generate a title for this conversation without any lead-in, punctuation, quotation marks, periods, symbols, bold text, or additional text. Remove enclosing quotation marks. Please only return the title without any additional info.",
        }
    ]
    title = await ask(
        endpoint,
        {
            "messages": messages
        }
    )

    convo.generate_title = False
    convo.title = title
    await topic.update_topic(convo)


def message_check(func):
    async def wrapper(message: Message, bot: AsyncTeleBot):
        if message.chat.type in ["group", "supergroup", "gigagroup", "channel"]:
            if not await is_mention_me(message):
                return

        await func(message, bot)

    return wrapper


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = message_check(decorator(handle_message))
    bot.register_message_handler(handler, regexp=r"^(?!/)", pass_bot=True, content_types=["text"])
