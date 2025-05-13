#!/usr/bin/env -S uv --quiet run --script

from bot import Bot
import asyncio
import discord
from config import CONFIG
import argparse

async def main():
    parser = argparse.ArgumentParser(description='Discord help agent')
    parser.add_argument('--allow-dms', action='store_true', help='Allow responding to DMs')
    args = parser.parse_args()

    intents = discord.Intents.default()
    intents.message_content = True
    discord.utils.setup_logging()

    client = await Bot.create(intents=intents, allow_dms=args.allow_dms)
    await client.start(CONFIG.DISCORD_TOKEN, reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())
