from telebot.async_telebot import AsyncTeleBot
from telebot import types as tg_types

from ..storage import types


def find_candidate(photo_list: list[tg_types.PhotoSize], width=640, height: int = 480):
    distance = width + height
    delta = 1000000
    candidate = None
    for photo in photo_list:
        new_delta = abs(photo.width + photo.height - distance)
        if new_delta < delta:
            delta = new_delta
            candidate = photo

    return candidate


async def download_image(
    bot: AsyncTeleBot, message: tg_types.Message, width=640, height: int = 480
) -> bytes:
    photo = find_candidate(message.photo, width=width, height=height)
    file = await bot.get_file(photo.file_id)

    return await bot.download_file(file.file_path)
