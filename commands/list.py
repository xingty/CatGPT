from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from utils.md2tgmd import escape
from context import profiles, session
from utils.text import messages_to_segments
from . import show_conversation


async def show_conversation_list(uid: str, msg_id: int, chat_id: int, bot: AsyncTeleBot, edit_msg_id: int = -1):
    profile = profiles.load(uid)
    convo_id = profile["conversation"].get(str(chat_id))
    current_convo = session.get_convo(uid, convo_id) or {}
    context = f'{msg_id}:{chat_id}:{uid}'
    keyboard = []
    items = []

    title = current_convo.get('title', 'None')
    text = f"Current conversation: `{title}` \n\nConversation list:\n"
    conversations = session.list_conversation(uid, chat_id)
    for index, convo in enumerate(conversations):
        seq = str(index + 1)
        callback_data = f'{action["name"]}:l_{convo["id"]}:{context}'
        if len(items) == 5:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(seq, callback_data=callback_data))
        text += f"{seq}. {convo['title']}\n"

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
    uid = str(message.from_user.id)
    await show_conversation_list(uid, message.message_id, message.chat.id, bot)


async def do_convo_change(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: str, message: Message):
    segs = operation.split('_')
    real_op = segs[0]
    conversation_id = segs[1]

    convo = session.get_convo(uid, conversation_id)
    if convo is None:
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f'conversation `{conversation_id}` not found')
        )
        return

    if real_op == "l":  # user click the button
        context = f'{message.message_id}:{message.chat.id}:{uid}'
        op_switch = f"s_{conversation_id}"
        # op_fetch = f"q_{conversation_id}"
        op_delete = f"d_{conversation_id}"
        op_cancel = f"c_{conversation_id}"

        buttons = [[
            InlineKeyboardButton("switch", callback_data=f'{action["name"]}:{op_switch}:{context}'),
            # InlineKeyboardButton("fetch", callback_data=f'{action["name"]}:{op_fetch}:{context}'),
            InlineKeyboardButton("delete", callback_data=f'{action["name"]}:{op_delete}:{context}'),
            InlineKeyboardButton("dismiss", callback_data=f'{action["name"]}:{op_cancel}:{context}'),
        ]]
        messages = convo.get("context", [])
        print("len", len(messages))
        fragments = []
        if len(messages) >= 2:
            fragments = [messages[-2], messages[-1]]

        summary = ""
        segments = messages_to_segments(fragments)
        if len(segments) > 0:
            summary = segments[0]

        message_preview = f"**What would you like to do on the conversation** `<{convo['title']}>`?\n\n{summary}"
        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(message_preview),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    elif real_op == "s":  # switch to this conversation
        profile = profiles.load(uid)
        profile["conversation"][str(chat_id)] = conversation_id
        profiles.update_all(uid, profile)
        await show_conversation(
            chat_id=chat_id,
            msg_id=msg_id,
            uid=uid,
            bot=bot,
            convo=convo,
        )
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    # elif real_op == "q":  # get content of this conversation
    #     await show_conversation(message, bot, uid, convo)
    elif real_op == "d":  # delete this conversation
        session.delete_convo(uid, conversation_id)
        messages = convo.get("context", [])
        message_ids = [msg["message_id"] for msg in messages if msg["role"] != "system"]
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
    "description": 'all conversations',
    "handler": do_convo_change,
    "delete_after_invoke": False
}
