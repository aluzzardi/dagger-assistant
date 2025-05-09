#!/usr/bin/env -S uv --quiet run --script

from bot import Bot
import asyncio
import discord
from config import CONFIG

async def main():
    # parser = argparse.ArgumentParser(description='Discord help agent')
    # parser.add_argument('--real-time', action='store_true', help='Run as real-time bot')
    # parser.add_argument('--single', action='store_true', help='Process a single question')
    # args = parser.parse_args()

    intents = discord.Intents.default()
    intents.message_content = True
    discord.utils.setup_logging()

    client = await Bot.create(intents=intents)
    await client.start(CONFIG.DISCORD_TOKEN, reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())
