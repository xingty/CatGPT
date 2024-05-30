from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message
from context import session, profiles, config, get_bot_name
from ask import ask_stream, ask
from utils.md2tgmd import escape
from utils.text import get_strip_text, get_timeout_from_text
from utils.prompt import get_prompt
from . import create_convo_and_update_profile
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
    if message.chat.type in ["group", "supergroup", "gigagroup", "channel"]:
        if not await is_mention_me(message):
            print("not a mention")
            return

    uid = str(message.from_user.id)
    chat_id = str(message.chat.id)
    profile = profiles.load(uid)
    convo_id = profile["conversation"].get(chat_id)
    convo = session.get_convo(uid, convo_id)
    if convo is None:
        convo = create_convo_and_update_profile(uid, message.chat.id, profile)

    endpoint = config.get_endpoint(profile.get("endpoint"))
    if endpoint is None:
        await bot.reply_to(
            message=message,
            text="Please select an endpoint to use."
        )
        return

    message_text = get_strip_text(message)
    messages = convo.get("context", []).copy()
    messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    messages.append({
        "role": "user",
        "content": message_text
    })
    model = profile.get("model")
    if model not in endpoint["models"]:
        model = endpoint["default_model"]

    reply_msg = await bot.reply_to(
        message=message,
        text="A smart cat is thinking..."
    )

    try:
        text = await do_reply(endpoint, model, messages, reply_msg, bot)
        convo["context"] += [
            {
                "role": "user",
                "content": message_text,
                'message_id': message.message_id,
                'chat_id': message.chat.id,
                'ts': int(time.time()),
            },
            {
                'role': 'assistant',
                'content': text,
                'message_id': reply_msg.message_id,
                'chat_id': message.chat.id,
                'ts': int(time.time()),
            }
        ]
        session.save_convo(uid, convo)

        generate_title = convo.get("generate_title", True)
        if generate_title:
            await do_generate_title(convo, messages, uid, text)
    except Exception as e:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reply_msg.message_id,
            text=f"Error: {e}"
        )
        return


async def do_reply(endpoint: dict, model: str, messages: list, reply_msg: Message, bot: AsyncTeleBot):
    text = ""
    buffered = ""
    start = time.time()
    timeout = 1.8
    async for chunk in ask_stream(endpoint, {
        "model": model,
        "messages": messages,
    }):
        content = chunk["content"]
        buffered += content if content is not None else ""
        finished = chunk["finished"] == "stop"
        if (time.time() - start > timeout and len(buffered) >= 18) or finished:
            start = time.time()
            try:
                await bot.edit_message_text(
                    text=escape(text + buffered),
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
                    timeout = 10 if seconds < 0 else seconds
                else:
                    raise ae

    if len(buffered) > 0:
        text += buffered
        delta = timeout - (time.time() - start)
        if delta > 0:
            await asyncio.sleep(int(delta) + 1)

        await bot.edit_message_text(
            text=escape(text),
            chat_id=reply_msg.chat.id,
            message_id=reply_msg.message_id,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )

    return text


async def do_generate_title(convo: dict, messages: list, uid: str, text: str):
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

    convo["generate_title"] = False
    convo["title"] = title
    session.save_convo(uid, convo)


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
