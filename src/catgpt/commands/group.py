from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ..context import group_config


async def handle_group_message(message: Message, bot: AsyncTeleBot) -> None:
    if "group" not in message.chat.type:
        return

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["creator", "administrator"]:
        await bot.reply_to(message, "Permission denied")
        return

    segments = message.text.strip().split(" ")
    if len(segments) > 1:
        operation = segments[1]
        await do_change_group_info(
            bot=bot,
            operation=operation,
            msg_ids=[message.message_id],
            chat_id=message.chat.id,
            uid=message.from_user.id,
            message=message,
        )
        return

    context = f"{message.message_id}:{message.chat.id}:{message.from_user.id}"
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f"respond:yes:{context}"),
            InlineKeyboardButton("No", callback_data=f"respond:no:{context}"),
        ],
    ]

    await bot.send_message(
        chat_id=message.chat.id,
        text="Are you sure?",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
        message_thread_id=message.message_thread_id,
    )


async def do_change_group_info(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: int,
    message: Message,
):
    enable = 1 if operation in ["y", "yes"] else 0
    await group_config.update_respond_messages(chat_id, enable)
    await bot.send_message(
        chat_id=chat_id,
        text=f"Responding to group messages: {'enabled' if enable else 'disabled'}",
        reply_to_message_id=msg_ids[0],
        message_thread_id=message.message_thread_id,
    )

    if msg_ids[0] != message.message_id:
        await bot.delete_message(chat_id, message.message_id)


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_group_message)
    bot.register_message_handler(handler, pass_bot=True, commands=["respond"])

    action_provider["respond"] = do_change_group_info


action = {
    "name": "respond",
    "description": "respond group message [y|n]",
}
