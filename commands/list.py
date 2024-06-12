from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from utils.md2tgmd import escape
from context import profiles, topic
from utils.text import messages_to_segments
from . import share


async def show_conversation_list(
        uid: int,
        msg_id: int,
        chat_id: int,
        bot: AsyncTeleBot,
        chat_type: str,
        edit_msg_id: int = -1
):
    profile = await profiles.load(uid)
    convo_id = profile.get_conversation_id(chat_type)

    current_convo = await topic.get_topic(convo_id)
    context = f'{msg_id}:{chat_id}:{uid}'
    keyboard = []
    items = []

    title = current_convo.title if current_convo else "None"
    text = f"Current topic: `{title}` \n\nlist of topics:\n"
    conversations = await topic.list_topics(int(uid), chat_id)
    for index, convo in enumerate(conversations):
        callback_data = f'{action["name"]}:l_{convo.tid}:{context}'
        if len(items) == 5:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(index+1, callback_data=callback_data))
        text += f"{index+1}. {convo.title}\n"

    if len(items) > 0:
        keyboard.append(items)

    if edit_msg_id <= 0:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
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
    await show_conversation_list(uid, message.message_id, message.chat.id, bot, message.chat.type)


async def do_convo_change(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: int, message: Message):
    segs = operation.split('_')
    real_op = segs[0]
    conversation_id = int(segs[1])

    convo = await topic.get_topic(conversation_id, fetch_messages=True)
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f'topic `{conversation_id}` not found')
        )
        return

    if real_op == "l":  # user click the button
        context = f'{message.message_id}:{message.chat.id}:{uid}'
        op_switch = f"s_{conversation_id}"
        op_share = f"sr_{conversation_id}"
        op_delete = f"d_{conversation_id}"
        op_cancel = f"c_{conversation_id}"

        buttons = [[
            InlineKeyboardButton("switch", callback_data=f'{action["name"]}:{op_switch}:{context}'),
            InlineKeyboardButton("share", callback_data=f'{action["name"]}:{op_share}:{context}'),
            InlineKeyboardButton("delete", callback_data=f'{action["name"]}:{op_delete}:{context}'),
            InlineKeyboardButton("dismiss", callback_data=f'{action["name"]}:{op_cancel}:{context}'),
        ]]
        messages = convo.messages
        fragments = []
        if len(messages) >= 2:
            fragments = [messages[-2], messages[-1]]

        summary = ""
        segments = messages_to_segments(fragments)
        if len(segments) > 0:
            summary = segments[0]

        message_preview = f"**What would you like to do on the topic** `<{convo.title}>`?\n\n{summary}"
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(message_preview),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    elif real_op == "s":  # switch to this conversation
        await profiles.update_conversation_id(uid, message.chat.type, conversation_id)
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f"Switched to topic `{convo.title}`"),
            reply_to_message_id=msg_id
        )
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    elif real_op == "sr":  # share this conversation to a share provider
        html_url = await share(convo)
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f"Share link: {html_url}"),
            disable_web_page_preview=False
        )
    elif real_op == "d":  # delete this conversation
        await topic.remove_topic(conversation_id)
        message_ids = [msg.message_id for msg in convo.messages if msg.role != "system"]
        try:
            if len(message_ids) > 0:
                await bot.delete_messages(chat_id=chat_id, message_ids=message_ids)
        except Exception as e:
            print(e)

        await show_conversation_list(
            uid=uid,
            msg_id=msg_id,
            chat_id=chat_id,
            bot=bot,
            chat_type=message.chat.type,
            edit_msg_id=msg_id
        )

    elif real_op == "c":  # cancel
        print(f"cancel operation {conversation_id}")

    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_convo)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])


action = {
    "name": 'list',
    "description": 'all topics',
    "handler": do_convo_change,
    "delete_after_invoke": False
}
