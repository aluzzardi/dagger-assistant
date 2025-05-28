#!/usr/bin/env -S uv --quiet run --script

from bot import Bot
from dev import MockBot
import asyncio
import discord
from config import CONFIG
import argparse
import logging

async def main():
    parser = argparse.ArgumentParser(description='Discord help agent')
    parser.add_argument('--allow-dms', action='store_true', help='Allow responding to DMs')
    parser.add_argument('--dev', action='store_true', help='Run in dev mode (no discord connection)')
    args = parser.parse_args()

    intents = discord.Intents.default()
    intents.message_content = True
    discord.utils.setup_logging()

    if args.dev:
        # In dev mode, remove some noise so we can see the actual output
        logging.basicConfig(level=logging.INFO)
        logging.getLogger('openai').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        client = await MockBot.create()
        await client.start()
        return

    client = await Bot.create(intents=intents, allow_dms=args.allow_dms)
    await client.start(CONFIG.DISCORD_TOKEN, reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())
