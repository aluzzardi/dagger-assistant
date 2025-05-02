#!/usr/bin/env -S uv --quiet run --script

import argparse
from bot import run_bot
import asyncio

async def main():
    # parser = argparse.ArgumentParser(description='Discord help agent')
    # parser.add_argument('--real-time', action='store_true', help='Run as real-time bot')
    # parser.add_argument('--single', action='store_true', help='Process a single question')
    # args = parser.parse_args()

    await run_bot()

if __name__ == "__main__":
    asyncio.run(main())
