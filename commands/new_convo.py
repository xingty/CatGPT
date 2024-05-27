from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from context import session, profiles
from utils.md2tgmd import escape


async def handle_new_topic(message: Message, bot: AsyncTeleBot) -> None:
    text = message.text.replace('/new', '').strip()
    uid = str(message.from_user.id)
    await create_convo(bot, message.message_id, message.chat.id, uid, text)
    # context = f'{message.message_id}:{message.chat.id}:{message.from_user.id}'
    # keyboard = [
    #     [
    #         InlineKeyboardButton("Yes", callback_data=f'{action["name"]}:yes:{context}'),
    #         InlineKeyboardButton("No", callback_data=f'{action["name"]}:no:{context}'),
    #     ],
    # ]
    #
    # reply_markup = InlineKeyboardMarkup(keyboard)
    # await bot.send_message(
    #     chat_id=message.chat.id,
    #     text='Create a new topic? (Yes/No)',
    #     reply_markup=reply_markup
    # )


async def create_convo(bot: AsyncTeleBot, msg_id: int, chat_id: int, uid: str, title: str = None) -> None:
    profile = profiles.load(uid)
    convo = session.create_convo(uid, title)
    profile["conversation_id"] = convo.get("id")
    profiles.update_all(uid, profile)

    text = (
        "A new topic has been created.\nCurrent conversation: `{title}`\nPrompt: `{prompt}`\nendpoint: `{""endpoint}` \nmodel: `{model}`".
        format(
            title=convo.get('title'),
            prompt=profile.get('role'),
            endpoint=profile.get('endpoint'),
            model=profile.get('model')
        ))

    await bot.send_message(
        chat_id=chat_id,
        text=escape(text),
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2"
    )


# async def do_create_topic(
#         bot: AsyncTeleBot, operation: str, msg_id: int,
#         chat_id: int, uid: str, message: Message
# ) -> None:
#     if operation == "yes":
#         await create_convo(bot, msg_id, chat_id, uid)


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_new_topic)
    bot.register_message_handler(handler, pass_bot=True, commands=['new'])


action = {
    "name": 'new',
    "description": 'New Topic',
    # "handler": do_create_topic,
}
