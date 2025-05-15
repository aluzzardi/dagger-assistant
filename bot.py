import discord
import json
from agent import AgentContext, Triager
from agents import Runner, trace

def format_message(message: discord.Message) -> dict:
    return json.dumps({
        "user": message.author.name,
        "created_at": message.created_at.isoformat(),
        "message": message.clean_content,
    })

def message_to_input(message: discord.Message, bot_user: discord.User):
    if message.author == bot_user:
        return {"content": message.clean_content, "role": "assistant"}
    return {"content": format_message(message), "role": "user"}

async def get_thread_starter_message(thread: discord.Thread) -> discord.Message | None:
    if thread.starter_message is not None:
        return thread.starter_message

    # If starter_message is not in cache, fetch the oldest message
    history = [message async for message in thread.history(limit=1, oldest_first=True)]
    if not history:
        return None
    return history[0]

class Bot(discord.Client):
    @classmethod
    async def create(self, *args, allow_dms: bool = False, **kwargs):
        triager = Triager()
        await triager.connect()

        return Bot(triager=triager, allow_dms=allow_dms, *args, **kwargs)

    def __init__(self, triager: Triager, allow_dms: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._triager = triager
        self._allow_dms = allow_dms

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    # Dispatch messages based on the channel type
    # async def on_message(self, message):
    #     print(f"Processing message: {message}")

    #     # Ignore our own messages
    #     if message.author == self.user:
    #         return

    #     if isinstance(message.channel, discord.Thread):
    #         await self.on_thread_message(message)
    #     elif isinstance(message.channel, discord.TextChannel):
    #         await self.on_channel_message(message)
    #     else:
    #         await message.reply(
    #             "I can only process messages in text channels or threads",
    #         )

    async def on_message(self, message: discord.Message):
        # Ignore our own messages
        if message.author == self.user:
            return

        # Check if it's a DM
        is_dm = isinstance(message.channel, discord.DMChannel)

        # Ignore DMs
        if not self._allow_dms and is_dm:
            await message.channel.send(
                "I can't talk to you in DMs, ask me again in a public channel",
            )
            return

        # Only consider messages where we're being mentioned *directly* (or DMs)
        if not is_dm and not self.user.mentioned_in(message):
            return
        if message.mention_everyone:
            return

        # Only process messages from the @DaggerTeam (or DMs)
        if not is_dm and not any(filter(lambda role: role.name == "Dagger Team", message.author.roles)):
            await message.channel.send(
                "I can only answer to Dagger Team members for now",
            )
            return

        query = {
            "mention": format_message(message),
        }
        if message.reference is not None:
            message_reference = await message.channel.fetch_message(message.reference.message_id)
            query["reference"] = format_message(message_reference)

        history = [message async for message in message.channel.history(limit=100)]
        history = sorted(history, key=lambda message: message.created_at)
        if history:
            query["history"] = [format_message(message) for message in history]

        print(f"Query: {query}")

        with trace("Processing channel message"):
            async with message.channel.typing():
                try:
                    triage_result = await Runner.run(
                        self._triager.agent,
                        json.dumps(query),
                        context=AgentContext(
                            user=message.author.name,
                        ),
                    )

                    print(f"> {triage_result.final_output}")
                    await message.reply(
                        content=triage_result.final_output,
                        suppress_embeds=True,
                    )

                    # Create a thread for the response
                    # assert isinstance(triage_result.final_output, SummaryOutput)
                    # thread = await message.create_thread(name=triage_result.final_output.title)
                    # await thread.send(
                    #     content=triage_result.final_output.summary,
                    #     # reference=message,
                    #     suppress_embeds=True,
                    # )
                except Exception as e:
                    await message.reply(
                        content=f"Error triaging message: {e}",
                        suppress_embeds=True,
                    )
                    raise

    async def on_thread_message(self, message: discord.Message):
        print(f"Processing thread message: {message}")
        starter_message = await get_thread_starter_message(message.channel)
        if starter_message is None:
            print("No starter message found")
        if starter_message.author != self.user:
            print(f"Didn't start the thread: {starter_message.author}")
            return
        print("I started this thread")

        history = [message async for message in message.channel.history(limit=100)]
        history = sorted(history, key=lambda message: message.created_at)

        inputs = [message_to_input(message, self.user) for message in history]

        with trace("Processing thread message"):
            async with message.channel.typing():
                try:
                    triage_result = await Runner.run(
                        self._triager.agent,
                        inputs,
                        context=AgentContext(
                            user=message.author.name,
                        ),
                    )

                    print(f"> {triage_result.final_output}")
                    await message.channel.send(
                        content=triage_result.final_output,
                        # reference=message,
                        suppress_embeds=True,
                    )
                except Exception as e:
                    await message.channel.send(
                        content=f"Error triaging message: {e}",
                        reference=message,
                        suppress_embeds=True,
                    )
