from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from utils.md2tgmd import escape
from context import profiles, session
from . import show_conversation


async def handle_convo(message: Message, bot: AsyncTeleBot):
    uid = str(message.from_user.id)
    profile = profiles.load(uid)
    current_convo = session.get_convo(uid, profile.get("conversation_id")) or {}
    context = f'{message.message_id}:{message.chat.id}:{uid}'
    keyboard = []
    items = []

    title = current_convo.get('title', 'None')
    text = f"Current conversation: `{title}` \n\nConversation list:\n"
    conversations = session.list_conversation(uid)
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

    await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


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
            InlineKeyboardButton("cancel", callback_data=f'{action["name"]}:{op_cancel}:{context}'),
        ]]

        await bot.send_message(
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            text=escape(f"What would you like to do on the conversation `<{convo['title']}>`?"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    elif real_op == "s":  # switch to this conversation
        profile = profiles.load(uid)
        profile["conversation_id"] = conversation_id
        profiles.update_all(uid, profile)
        await show_conversation(
            chat_id=chat_id,
            msg_id=msg_id,
            uid=uid,
            bot=bot,
            convo=convo,
        )
    # elif real_op == "q":  # get content of this conversation
    #     await show_conversation(message, bot, uid, convo)
    elif real_op == "d":  # delete this conversation
        print(f"delete {conversation_id}")
        session.delete_convo(uid, conversation_id)
    elif real_op == "c":  # cancel
        print(f"cancel operation {conversation_id}")

    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_convo)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])


action = {
    "name": 'convo',
    "description": 'all conversations',
    "handler": do_convo_change,
    "delete_after_invoke": False
}
