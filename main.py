from telebot.async_telebot import AsyncTeleBot
import asyncio
import argparse
import context


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help="Config file",
    )

    options = parser.parse_args()
    await context.init(options)
    bot: AsyncTeleBot = context.bot

    from commands import register_commands
    await register_commands(bot)
    await bot.infinity_polling()


if __name__ == '__main__':
    asyncio.run(main())
