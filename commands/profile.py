from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from utils.md2tgmd import escape
from context import profiles
from . import get_profile_text


async def handle_profiles(message: Message, bot: AsyncTeleBot):
    context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
    keyboard = []
    items = []
    for name in profiles.presets.keys():
        callback_data = f'profile:{name}:{context}'
        if len(items) == 3:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(name, callback_data=callback_data))

    if len(items) > 0:
        keyboard.append(items)

    profile = await profiles.load(message.from_user.id)
    state_text = await get_profile_text(profile, message.chat.type)

    await bot.send_message(
        chat_id=message.chat.id,
        text=state_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )


async def do_profile_change(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: int, message: Message):
    profile = await profiles.update_preset(uid, operation)
    text = await get_profile_text(profile, message.chat.type)

    await bot.send_message(
        chat_id=chat_id,
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2",
        text=escape(text)
    )


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_profiles)
    bot.register_message_handler(handler, pass_bot=True, commands=['profile'])


action = {
    "name": 'profile',
    "description": 'show presets',
    "handler": do_profile_change,
    "delete_after_invoke": False
}
