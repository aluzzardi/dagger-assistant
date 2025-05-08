import discord
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.agents import LlmAgent, RunConfig
from google.adk.runners import Runner

from config import CONFIG
from agent import create_triage_agent


def format_message(message: discord.Message) -> str:
    return f"<context><user>{message.author.name}</user></context>{message.content}"

def message_to_input(message: discord.Message, bot_user: discord.User):
    if message.author == bot_user:
        return {"content": message.content, "role": "assistant"}
    return {"content": format_message(message), "role": "user"}

class Bot(discord.Client):
    @classmethod
    async def create(self, *args, **kwargs):
        # FIXME: exit_stack?
        tools, exit_stack = await MCPToolset.from_server(
            connection_params=StdioServerParameters(
                command="docker",
                args=[
                    "run",
                    "-i",
                    "--rm",
                    "-e",
                    "GITHUB_PERSONAL_ACCESS_TOKEN=" + CONFIG.GITHUB_TOKEN,
                    "ghcr.io/github/github-mcp-server"
                ],
            ),
        )

        triage_agent = await create_triage_agent(tools)

        return Bot(triage_agent, *args, **kwargs)

    def __init__(self, triage_agent: LlmAgent, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._triage_agent = triage_agent

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):
        print(f"Processing message: {message}")

        if message.author == self.user:
            return

        if not self.user.mentioned_in(message):
            return


        inputs: list[TResponseInputItem] = []
        inputs.append({"content": format_message(message), "role": "user"})
        # If the message is a reply, add the referenced message to the input
        if message.reference is not None:
            message_reference = await message.channel.fetch_message(message.reference.message_id)
            inputs.insert(0, {"content": format_message(message_reference), "role": "user"})

        # Grab the channel history as context
        history = [message_to_input(message, self.user) async
            for message in message.channel.history(limit=50)
        ]
        if history:
            print(f"History: {history}")
            inputs = history + inputs

        # with trace("Processing message"):
        async with message.channel.typing():
            try:
                config = RunConfig()
                runner = Runner(agent=self._triage_agent)
                triage_result = await runner.run_async(user_id=self.user.id, new_message=inputs, run_config=config)

                # FIXME: not using typed outputs right now
                # assert isinstance(triage_result.final_output, TriageOutput)

                print(f"> {triage_result.final_output}")
                await message.channel.send(
                    content=triage_result.final_output,
                    reference=message,
                    suppress_embeds=True,
                )
            except Exception as e:
                await message.channel.send(
                    content=f"Error triaging message: {e}",
                    reference=message,
                    suppress_embeds=True,
                )

async def run_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    discord.utils.setup_logging()

    client = await Bot.create(intents=intents)
    await client.start(CONFIG.DISCORD_TOKEN, reconnect=True)
