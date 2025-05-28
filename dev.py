import json
from datetime import datetime

from agent import AgentContext, Triager
from agents import Runner, trace


class MockUser:
    def __init__(self):
        self.name = "test"

def format_message(message: str) -> dict:
    return json.dumps({
        "user": "test",
        "created_at": datetime.now().isoformat(),
        "message": message,
    })

class MockBot:
    @classmethod
    async def create(self, *args, **kwargs):
        triager = Triager()
        await triager.connect()
        return MockBot(triager=triager, *args, **kwargs)

    def __init__(self, triager: Triager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._triager = triager
        self.user = MockUser()

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message: str):
        print(f"Processing message: {message}")

        query = {
            "mention": format_message(message),
        }
        # TODO: add "reference" and "history" keys
        # potentially load discord history from a file

        triage_result = await Runner.run(
            self._triager.agent,
            json.dumps(query),
            context=AgentContext(
                user=self.user.name,
            ),
        )

        print(f"> {triage_result.final_output}")

    async def start(self):        
        await self.on_ready()
        while True:
            message = input("> ")
            message = message.strip()
            if not message:
                continue
            await self.on_message(message)
