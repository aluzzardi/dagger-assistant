from dataclasses import dataclass
from typing import List

@dataclass
class AgentConfig:
    OPENAI_API_KEY: str
    DISCORD_TOKEN: str
    GITHUB_TOKEN: str
    GITHUB_REPO: str
    TARGET_CHANNELS: List[str]

# Load from environment variables
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = AgentConfig(
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
    DISCORD_TOKEN=os.getenv("DISCORD_TOKEN"),
    GITHUB_TOKEN=os.getenv("GITHUB_TOKEN"),
    GITHUB_REPO=os.getenv("GITHUB_REPO", "dagger/dagger"),
    TARGET_CHANNELS=["help"],
)
