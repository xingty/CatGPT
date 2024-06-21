from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from ..context import topic, profiles, get_bot_name
from ..utils.md2tgmd import escape
from ..utils.prompt import get_prompt
from . import get_profile_text
from ..storage import tx


async def handle_new_topic(message: Message, bot: AsyncTeleBot) -> None:
    bot_name = await get_bot_name()
    text = message.text.replace("/new", "").replace(bot_name, "").strip()
    uid = message.from_user.id

    await create_convo(
        bot=bot,
        msg_id=message.message_id,
        chat_id=message.chat.id,
        uid=uid,
        chat_type=message.chat.type,
        title=text,
        thread_id=message.message_thread_id,
    )


@tx.transactional(tx_type="write")
async def create_topic_and_update_profile(
    chat_id: int,
    uid: int,
    chat_type: str,
    thread_id: int = 0,
    title: str = None,
    messages: list = None,
):
    convo = await topic.new_topic(
        title=title,
        chat_id=chat_id,
        user_id=uid,
        messages=messages,
        generate_title=title is None or len(title) == 0,
        thread_id=thread_id,
    )
    await profiles.update_conversation_id(uid, chat_id, thread_id, convo.tid)
    return convo


async def create_convo(
    bot: AsyncTeleBot,
    msg_id: int,
    chat_id: int,
    uid: int,
    chat_type: str,
    title: str = None,
    thread_id: int = None,
) -> None:
    profile = await profiles.load(uid, chat_id, thread_id)
    prompt = get_prompt(profiles.get_prompt(profile.prompt))
    messages = [prompt] if prompt else None
    convo = await create_topic_and_update_profile(
        chat_id=chat_id,
        uid=uid,
        chat_type=chat_type,
        thread_id=thread_id,
        title=title,
        messages=messages,
    )

    profile.topic_id = convo.tid
    text = await get_profile_text(profile, chat_type)
    text = "A new topic has been created.\n" + text

    await bot.send_message(
        chat_id=chat_id,
        text=escape(text),
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2",
        message_thread_id=thread_id,
    )


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_new_topic)
    bot.register_message_handler(handler, pass_bot=True, commands=["new"])

    return action


action = {"name": "new", "description": "start a new topic: [title]", "order": 10}
