from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from telebot.types import Message
from utils.md2tgmd import escape
from context import session, profiles, config
from utils.text import messages_to_segments
from share.github import create_or_update_issue
from . import show_conversation


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
    convo_id = profile["conversation"].get(str(message.chat.id))
    convo = session.get_convo(uid, convo_id)
    if convo is None:
        text = "Conversation not found. Please start a new conversation or switch to a existing one."
        await bot.reply_to(message, text)
        return

    await show_conversation(
        chat_id=message.chat.id,
        msg_id=message.message_id,
        uid=uid,
        bot=bot,
        convo=convo,
        reply_msg_id=message.message_id
    )


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
        if not config.share_info:
            await bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=msg_id,
                parse_mode="MarkdownV2",
                text=escape(f"Please set share info in config")
            )
            return

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
        # 当点击yes时，real_op就是conversation_id
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
    "description": "current conversation",
    "handler": handle_share_convo,
    "delete_after_invoke": False
}
