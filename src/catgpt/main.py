import asyncio
import argparse

from telebot.async_telebot import AsyncTeleBot, types

from . import context


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Config file",
    )

    parser.add_argument(
        "--preset",
        type=str,
        required=False,
        help="preset file",
    )

    parser.add_argument(
        "--db-file",
        type=str,
        required=False,
        help="database file",
    )

    options = parser.parse_args()
    await context.init(options)
    bot: AsyncTeleBot = context.bot

    from .commands import register_commands

    await register_commands(bot)
    print("CatGPT is running...")
    await bot.infinity_polling(interval=1)


def launch():
    asyncio.run(main())


if __name__ == "__main__":
    launch()
