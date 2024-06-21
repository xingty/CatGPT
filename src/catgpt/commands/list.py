from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.md2tgmd import escape
from ..utils.text import encode_message_id
from ..context import profiles, topic
from ..utils.text import messages_to_segments, MAX_TEXT_LENGTH
from . import share, send_file


async def show_conversation_list(
    uid: int,
    msg_id: int,
    chat_id: int,
    bot: AsyncTeleBot,
    chat_type: str,
    thread_id: int = 0,
    edit_msg_id: int = -1,
):
    profile = await profiles.load(uid, chat_id, thread_id)
    convo_id = profile.topic_id

    current_convo = await topic.get_topic(convo_id)
    context = f"{msg_id}:{chat_id}:{uid}"
    keyboard = []
    items = []

    title = current_convo.title if current_convo else "None"
    text = f"Current topic: `{title}` \n\nlist of topics:\n"
    conversations = await topic.list_topics(int(uid), chat_id, thread_id)
    for index, convo in enumerate(conversations):
        callback_data = f"list_tips:{convo.tid}:{context}"
        if len(items) == 5:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(index + 1, callback_data=callback_data))
        text += f"{index+1}. {convo.title}\n"

    if len(items) > 0:
        keyboard.append(items)
        keyboard.append(
            [
                InlineKeyboardButton(
                    "dismiss", callback_data=f"list_tips:dismiss:{context}"
                )
            ]
        )

    # update list
    if edit_msg_id <= 0:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            message_thread_id=thread_id,
        )
    else:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=edit_msg_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_convo(message: Message, bot: AsyncTeleBot):
    uid = message.from_user.id
    await show_conversation_list(
        uid,
        message.message_id,
        message.chat.id,
        bot,
        message.chat.type,
        message.message_thread_id,
    )


async def do_convo_change(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: int,
    message: Message,
):
    segs = operation.split("_")
    real_op = segs[0]
    conversation_id = int(segs[1])

    convo = await topic.get_topic(conversation_id, fetch_messages=True)
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f"topic `{conversation_id}` not found"),
        )
        return

    elif real_op == "s":  # switch to this conversation
        await profiles.update_conversation_id(
            uid, chat_id, message.message_thread_id, conversation_id
        )
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f"Switched to topic `{convo.title}`"),
            message_thread_id=message.message_thread_id,
        )
        await bot.delete_messages(chat_id, [message.message_id] + msg_ids)
        return
    elif real_op == "sr":  # share this conversation to a share provider
        if len(convo.messages) > 0:
            html_url = await share(convo)
            await bot.send_message(
                chat_id=chat_id,
                parse_mode="MarkdownV2",
                text=escape(f"Share link: {html_url}"),
                disable_web_page_preview=False,
                message_thread_id=message.message_thread_id,
            )
    elif real_op == "dl":
        await send_file(bot, message, convo)
    elif real_op == "d":  # delete this conversation
        await topic.remove_topic(conversation_id)
        await show_conversation_list(
            uid=uid,
            msg_id=msg_ids[0],
            chat_id=chat_id,
            bot=bot,
            chat_type=message.chat.type,
            edit_msg_id=msg_ids[1],
            thread_id=message.message_thread_id,
        )
    elif real_op == "c":  # cancel
        print("on click dismiss")

    await bot.delete_message(chat_id, message.message_id)


async def do_handle_tips(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: int,
    message: Message,
):
    if operation == "dismiss":
        await bot.delete_messages(chat_id, [message.message_id, msg_ids[0]])
        return

    conversation_id = int(operation)
    convo = await topic.get_topic(conversation_id, fetch_messages=True)
    my_message_ids = msg_ids + [message.message_id]
    encoded_ids = encode_message_id(my_message_ids)

    context = f"{encoded_ids}:{message.chat.id}:{uid}"
    op_switch = f"s_{conversation_id}"
    op_share = f"sr_{conversation_id}"
    op_dl = f"dl_{conversation_id}"
    op_delete = f"d_{conversation_id}"
    op_cancel = f"c_{conversation_id}"

    buttons = [
        [
            InlineKeyboardButton(
                "switch", callback_data=f'{action["name"]}:{op_switch}:{context}'
            ),
            InlineKeyboardButton(
                "share", callback_data=f'{action["name"]}:{op_share}:{context}'
            ),
            InlineKeyboardButton(
                "download", callback_data=f'{action["name"]}:{op_dl}:{context}'
            ),
            InlineKeyboardButton(
                "delete", callback_data=f'{action["name"]}:{op_delete}:{context}'
            ),
        ],
        [
            InlineKeyboardButton(
                "dismiss", callback_data=f'{action["name"]}:{op_cancel}:{context}'
            )
        ],
    ]
    messages = convo.messages
    fragments = []
    if len(messages) >= 2:
        fragments = [messages[-2], messages[-1]]

    summary = ""
    segments = messages_to_segments(fragments)
    if len(segments) > 0:
        summary = segments[0]

    preview_message = (
        f"**What would you like to do on the topic** `<{convo.title}>`?\n\n{summary}"
    )
    preview_message = escape(preview_message)
    if len(preview_message) > MAX_TEXT_LENGTH:
        preview_message = preview_message[: MAX_TEXT_LENGTH - 3] + "..."

    await bot.send_message(
        chat_id=chat_id,
        parse_mode="MarkdownV2",
        text=preview_message,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_convo)
    bot.register_message_handler(handler, pass_bot=True, commands=[action["name"]])

    action_provider["list_tips"] = do_handle_tips
    action_provider[action["name"]] = do_convo_change

    return action


action = {
    "name": "list",
    "description": "all topics",
    "delete_after_invoke": False,
    "order": 20,
}
