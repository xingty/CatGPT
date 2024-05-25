from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from telebot.types import Message
from utils.md2tgmd import escape
from context import session, profiles, config
from utils.text import messages_to_segments
from share.github import create_or_update_issue


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


async def handle_conversation(message: Message, bot: AsyncTeleBot):
    uid = str(message.from_user.id)
    profile = profiles.load(uid)
    convo_id = profile.get("conversation_id")

    convo = session.get_convo(uid, convo_id)
    if convo is None:
        await bot.reply_to(message, "Please select a conversation to use.")
        return

    messages = convo.get("context", [])
    messages = [msg for msg in messages if (msg["role"] != "system" and msg["chat_id"] == message.chat.id)]
    segments = messages_to_segments(messages)
    if len(segments) == 0:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Content is empty, Please talk something.",
            reply_to_message_id=message.message_id
        )
        return

    last_message_id = message.message_id
    context = f'{message.message_id}:{message.chat.id}:{uid}'
    callback_data = f'{action["name"]}:share_{convo_id}:{context}'

    for content in segments:
        reply_msg: Message = await bot.send_message(
            chat_id=message.chat.id,
            text=escape(content),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_to_message_id=last_message_id,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Share", callback_data=callback_data)]]),
        )
        last_message_id = reply_msg.message_id


async def handle_share_convo(
        bot: AsyncTeleBot,
        operation: str,
        msg_id: int,
        chat_id: int,
        uid: str,
        message: Message
):
    segs = operation.split('_')
    real_op = segs[0]

    if real_op == "share":
        convo_id = segs[1]
        convo = session.get_convo(uid, convo_id)
        if convo is None:
            await bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=msg_id,
                parse_mode="MarkdownV2",
                text=escape(f'conversation not found')
            )
            return

        context = f'{message.message_id}:{message.chat.id}:{uid}'
        buttons = [[
            InlineKeyboardButton("yes", callback_data=f'{action["name"]}:{convo_id}:{context}'),
            InlineKeyboardButton("no", callback_data=f'{action["name"]}:no:{context}'),
        ]]

        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=msg_id,
            parse_mode="MarkdownV2",
            text=escape(f"Share this conversation `<{convo['title']}>` to github?"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif real_op == "no":
        await bot.delete_message(message.chat.id, message.message_id)
    else:
        convo = session.get_convo(uid, real_op)
        if convo is None:
            await bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=msg_id,
                parse_mode="MarkdownV2",
                text=escape(f'conversation not found')
            )
        else:
            html_url = await share(convo)
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    parse_mode="MarkdownV2",
                    text=escape(f"Share link: {html_url}"),
                    disable_web_page_preview=False
                )
            except Exception as e:
                await bot.send_message(
                    chat_id=chat_id,
                    parse_mode="MarkdownV2",
                    text=str(e),
                    disable_web_page_preview=True
                )

        await bot.delete_message(message.chat.id, message.message_id)


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_conversation)
    bot.register_message_handler(handler, pass_bot=True, commands=['conversation'])


action = {
    "name": "conversation",
    "description": "Current conversation",
    "handler": handle_share_convo,
    "delete_after_invoke": False
}
