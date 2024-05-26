from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message
from context import session, profiles, config, get_bot_name
from ask import ask_stream, ask
from utils.md2tgmd import escape
from utils.text import get_strip_text, get_timeout_from_text
import time


async def is_mention_me(message: Message) -> bool:
    if message.entities is None:
        return False
    bot_name = await get_bot_name()

    text = message.text
    for entity in message.entities:
        print(entity)
        if entity.type == "mention":
            who = text[entity.offset:entity.offset + entity.length]
            if who == bot_name:
                return True

    return False


async def handle_message(message: Message, bot: AsyncTeleBot) -> None:
    if message.chat.type in ["group", "supergroup", "gigagroup", "channel"]:
        if not await is_mention_me(message):
            print("not a mention")
            return

    uid = str(message.from_user.id)
    profile = profiles.load(uid)
    convo_id = profile.get("conversation_id")
    if convo_id is None:
        await bot.reply_to(
            message=message,
            text="Please select a conversation to use."
        )
        return
    convo = session.get_convo(uid, convo_id)
    if convo is None:
        await bot.reply_to(
            message=message,
            text="Please select a conversation to use."
        )
        return

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

    text = ""
    buffered = ""
    start = time.time()
    timeout = 1.8
    try:
        async for chunk in ask_stream(endpoint, {
            "model": model,
            "messages": messages,
        }):
            content = chunk["content"]
            buffered += content if content is not None else ""
            finished = chunk["finished"] == "stop"
            if (time.time() - start > timeout and len(buffered) >= 15) or finished:
                text += buffered
                buffered = ""
                start = time.time()
                try:
                    await bot.edit_message_text(
                        text=escape(text),
                        chat_id=message.chat.id,
                        message_id=reply_msg.message_id,
                        parse_mode="MarkdownV2",
                        disable_web_page_preview=True
                    )
                    timeout = 1.8
                except ApiTelegramException as ae:
                    print(ae)
                    if ae.error_code != 429:
                        raise ae

                    seconds = get_timeout_from_text(ae.description)
                    timeout = 10 if seconds < 0 else seconds

    except Exception as e:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reply_msg.message_id,
            text=f"Error: {e}"
        )
        return

    if message.content_type != "photo":
        convo["context"] += [
            {
                "role": "user",
                "content": message_text,
                'message_id': message.id,
                'chat_id': message.chat.id,
                'ts': int(time.time()),
            },
            {
                'role': 'assistant',
                'content': text,
                'message_id': message.id,
                'chat_id': message.chat.id,
                'ts': int(time.time()),
            }
        ]

        session.save_convo(uid, convo)

    generate_title = convo.get("generate_title", True)
    if generate_title:
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
    bot.register_message_handler(handler, regexp=r"^(?!/)", pass_bot=True, content_types=["text", "photo"])
