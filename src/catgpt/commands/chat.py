from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message

from ..context import profiles, config, get_bot_name, topic, group_config, page_preview
from ..types import Endpoint, MessageType, Preview
from ..utils.text import get_timeout_from_text, MAX_TEXT_LENGTH
from . import create_convo_and_update_profile
from ..provider import ask, ask_stream
from ..utils.md2tgmd import escape
from ..storage import types
from ..utils import tg_image

import time
import asyncio
import base64
import logging


async def is_mention_me(message: Message) -> bool:
    if message.entities is None:
        return False

    bot_name = await get_bot_name()
    text = message.text
    for entity in message.entities:
        if entity.type == "mention":
            who = text[entity.offset : entity.offset + entity.length]
            if who == bot_name:
                return True

    return False


async def send_message(bot: AsyncTeleBot, message: Message, text: str):
    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(text),
        reply_to_message_id=message.message_id,
    )


async def handle_message(message: Message, bot: AsyncTeleBot) -> None:
    message_text = (message.text or "").strip()
    if message.chat.type in ["group", "supergroup", "gigagroup", "channel"]:
        if await is_mention_me(message):
            bot_name = await get_bot_name()
            message_text = message_text.replace(bot_name, "").strip()
            message.text = message_text

    uid = message.from_user.id
    chat_id = message.chat.id
    profile = await profiles.load(uid, chat_id, message.message_thread_id)
    convo_id = profile.topic_id

    endpoint: Endpoint = config.get_endpoint(profile.endpoint)
    if endpoint is None:
        await bot.reply_to(message=message, text="Please select an endpoint to use.")
        return

    model = profile.model
    if model not in endpoint.models:
        model = endpoint.default_model

    img_data = None
    if message.content_type == "text":
        if not message_text:
            await bot.reply_to(message=message, text="Please enter a message.")
            return
    elif message.content_type == "photo":
        if not endpoint.is_support(model, message.content_type):
            await bot.reply_to(
                message=message, text="This model does not support this message type."
            )
            return

        bin_data = await tg_image.download_image(bot, message, width=800, height=600)
        img_data = base64.b64encode(bin_data).decode("utf-8")

    convo = await topic.get_topic(convo_id, fetch_messages=True)
    if convo is None:
        convo = await create_convo_and_update_profile(
            uid=uid,
            chat_id=chat_id,
            profile=profile,
            chat_type=message.chat.type,
            thread_id=message.message_thread_id,
        )

    messages = [
        m
        for m in convo.messages
        if m.message_type != MessageType.REASONING_CONTENT.value
    ]
    msg_type = MessageType[message.content_type.upper()]
    prompt_message = types.Message(
        role="user",
        content=message_text if msg_type.is_text() else message.caption,
        message_id=message.message_id,
        chat_id=chat_id,
        topic_id=convo_id,
        ts=int(time.time()),
        message_type=msg_type.value,
    )
    prompt_message.media_url = img_data
    messages.append(prompt_message)

    reply_msg = await bot.reply_to(message=message, text="A smart cat is thinking...")
    message.text = message_text if msg_type.is_text() else img_data
    # await topic.save_or_update_message_holder(convo_id, message, reply_msg.message_id)

    text = ""
    try:
        text, reasoning_content = await do_reply(
            endpoint, model, messages, reply_msg, bot, convo
        )
        reply_msg.text = text
        await topic.append_messages(convo_id, message, reply_msg, reasoning_content)

        try:
            if convo.generate_title:
                await do_generate_title(convo, messages, uid, text, endpoint)
        except Exception as ie:
            print(ie)
    except Exception as e:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reply_msg.message_id,
            text=f"{text}\n Error: {e}",
        )
        logging.exception(e)


async def do_reply(
    endpoint: Endpoint,
    model: str,
    messages: list,
    reply_msg: Message,
    bot: AsyncTeleBot,
    convo: types.Topic,
):
    text = ""
    buffered = ""
    start = time.time()
    timeout = 1.8
    text_overflow = False
    tmp_info = f"*{endpoint.name},   {model.lower()}*: \n\n"
    reasoning_content = ""
    newline = False

    async for chunk in await ask_stream(
        endpoint,
        {
            "model": model,
            "messages": messages,
        },
    ):
        content = chunk["content"]
        if chunk.get("reasoning"):
            reasoning_content += content
            newline = True
        elif newline:
            content = "\n\n---\n" + content
            newline = False
        elif not content:
            print("empty chunk's content", chunk)
            continue

        buffered += content
        finished = chunk["finished"] == "stop"

        if text_overflow:
            continue

        if (time.time() - start > timeout and len(buffered) >= 18) or finished:
            start = time.time()
            try:
                message_text = escape(f"{tmp_info}{text}{buffered}")
                if len(message_text) > MAX_TEXT_LENGTH:
                    text_overflow = True
                    continue

                await bot.edit_message_text(
                    text=message_text,
                    chat_id=reply_msg.chat.id,
                    message_id=reply_msg.message_id,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True,
                )
                text += buffered
                buffered = ""
                timeout = 1.8
            except ApiTelegramException as ae:
                print(ae)
                if ae.error_code == 400:
                    timeout = 2.5
                    print(escape(text + buffered))
                elif ae.error_code == 429:
                    seconds = get_timeout_from_text(ae.description)
                    timeout = 10 if seconds < 0 else seconds + 1
                else:
                    raise ae

    delta = timeout - (time.time() - start)
    if delta > 0:
        await asyncio.sleep(int(delta) + 1)

    msg_text = escape(text + buffered)
    if text_overflow or len(msg_text) > MAX_TEXT_LENGTH:
        if config.topic_preview == Preview.TELEGRAPH:
            msg_text = text + buffered
            title = f"{convo.title}_{reply_msg.message_id}"
            url = await page_preview.preview_chat(convo.label, title, msg_text)
            await bot.edit_message_text(
                chat_id=reply_msg.chat.id,
                message_id=reply_msg.message_id,
                text=url,
                disable_web_page_preview=False,
            )

            if len(reasoning_content) > 0:
                msg_text = fullText[len(reasoning_content) + 6 :]
            return msg_text, reasoning_content

        text_overflow = True
        msg_text = escape(text)

    msg = await bot.edit_message_text(
        text=msg_text,
        chat_id=reply_msg.chat.id,
        message_id=reply_msg.message_id,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
    )

    if text_overflow:
        await bot.send_message(
            chat_id=reply_msg.chat.id,
            text=escape(buffered),
            reply_to_message_id=msg.message_id,
        )

    fullText = text + buffered
    if len(reasoning_content) > 0:
        fullText = fullText[len(reasoning_content) + 6 :]

    return fullText, reasoning_content


async def do_generate_title(
    convo: types.Topic, messages: list, uid: int, text: str, current: Endpoint
):
    endpoint = current if current.generate_title else config.get_title_endpoint()[0]
    if endpoint is None:
        return

    title_prompt = "Please generate a title for this conversation without any lead-in, punctuation, quotation marks, periods, symbols, bold text, or additional text. Remove enclosing quotation marks. Please only return the title without any additional info."

    title_messages = messages + [
        types.Message(
            role="assistant",
            content=text,
            message_id=0,
            chat_id=0,
            topic_id=0,
            ts=int(time.time()),
            message_type=0,
        ),
        types.Message(
            role="user",
            content=title_prompt,
            message_id=0,
            chat_id=0,
            topic_id=0,
            ts=int(time.time()),
            message_type=0,
        ),
    ]
    title = await ask(endpoint, {"messages": title_messages})

    convo.generate_title = False
    convo.title = title
    await topic.update_topic(convo)


async def handle_document(message: Message, bot: AsyncTeleBot):
    mime_type = message.document.mime_type
    if not mime_type.startswith("text/"):
        await bot.reply_to(
            message,
            f"Unsupported file type: {mime_type}. Please use a text file.",
        )
        return

    caption = message.caption or ""
    file = await bot.get_file(message.document.file_id)
    content = await bot.download_file(file.file_path)
    content = content.decode("utf-8")

    message.text = f"{content}\n\n{caption}"
    await handle_message(message, bot)


class SegmentationHandler:
    def __init__(self):
        self.buffers = {}
        self.MAX_SEGMENTS = 50
        self.START_MARK = "===segstart"
        self.END_MARK = "===segend"
        self.CANCEL_MARK = "===segcancel"

    def _get_content_between_marks(self, text: str) -> str:
        """Extract content between segmentation marks if they exist"""
        if self.START_MARK in text and text.endswith(self.END_MARK):
            start_idx = text.index(self.START_MARK) + len(self.START_MARK)
            end_idx = text.rindex(self.END_MARK)
            return text[start_idx:end_idx].strip()
        return text

    def _is_in_segmentation_mode(self, uid: str) -> bool:
        return uid in self.buffers

    def process_message(self, message: Message, uid: str) -> tuple[str, bool]:
        """
        Process message and return (processed_text, should_handle)
        where should_handle indicates if the message should be handled by the bot
        """
        if message.content_type != "text":
            return message.text, True

        text = message.text.strip()

        # Handle single message containing both marks
        processed_text = self._get_content_between_marks(text)
        if processed_text != text:
            return processed_text, True

        # Handle segmentation mode
        if text.startswith(self.START_MARK):
            self.buffers[uid] = [text.replace(self.START_MARK, "").strip()]
            return "", False

        if text == self.CANCEL_MARK:
            if self._is_in_segmentation_mode(uid):
                del self.buffers[uid]
            return "", False

        if text.endswith(self.END_MARK):
            if not self._is_in_segmentation_mode(uid):
                return text, True

            current_text = text[: -len(self.END_MARK)].strip()
            if current_text:
                self.buffers[uid].append(current_text)

            combined_text = "\n".join(self.buffers[uid])
            del self.buffers[uid]
            return combined_text, True

        if self._is_in_segmentation_mode(uid):
            if len(self.buffers[uid]) < self.MAX_SEGMENTS:
                self.buffers[uid].append(text)
            return "", False

        return text, True


segmentation = SegmentationHandler()


def message_check(func):
    async def wrapper(message: Message, bot: AsyncTeleBot):
        if message.chat.type in ["group", "supergroup", "gigagroup", "channel"]:
            respond_message = await group_config.is_respond_group_message(
                message.chat.id
            )
            if not respond_message and not await is_mention_me(message):
                return

        uid = (
            f"{message.from_user.id}_{message.chat.id}_{message.message_thread_id or 0}"
        )

        processed_text, should_handle = segmentation.process_message(message, uid)
        if should_handle:
            message.text = processed_text
            await func(message, bot)

    return wrapper


def register(bot: AsyncTeleBot, decorator, provider) -> None:
    handler = decorator(message_check(handle_message))
    bot.register_message_handler(
        handler, regexp=r"^(?!/)", pass_bot=True, content_types=["text"]
    )
    bot.register_message_handler(handler, pass_bot=True, content_types=["photo"])
    doc_handler = decorator(message_check(handle_document))
    bot.register_message_handler(doc_handler, pass_bot=True, content_types=["document"])
