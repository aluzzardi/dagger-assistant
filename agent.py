import json
import os
from enum import Enum
from pydantic import BaseModel
from config import CONFIG
from agents import (
    Agent,
)
from agents.mcp import MCPServer, MCPServerStdio
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

class AgentContext(BaseModel):
    user: str | None = None

class TriageKindEnum(str, Enum):
    question = 'question'
    bug_report = 'bug_report'

def _github_agent(github_server: MCPServer) -> Agent[AgentContext]:
    return Agent[AgentContext](
        name="GitHub Agent",
        model="gpt-4.1",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            f"""
            You are a helpful GitHub agent. Use your tools to interact with GitHub. You may browse pull requests, commits, etc.
            If you are not sure what to do, or if you're missing some critical information, ask the user for more information.
            If you end up creating or updating an issue, always reference the issue URL in your response.
            If the repository name is not specified, use the default repository: {CONFIG.GITHUB_REPO}
            """
        ),
        mcp_servers=[github_server],
    )

def _issue_agent(github_server: MCPServer) -> Agent[AgentContext]:
    return Agent[AgentContext](
        name="Issue Agent",
        model="gpt-4.1",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            f"""
            You are a helpful agent responsible for creating and updating GitHub issues. Use your tools to interact with GitHub.
            Issues might be bug reports, feature requests, or other types of requests.
            Your job is to gather as much information as possible from the user's message and the whole conversation.
            If you are not sure what to do, or if you're missing some critical information, ask the user for more information.

            Example of required information:
            - Short summary
            - Detailed description with collected information from the conversation
            - If it's a bug report:
                - Reproduction steps and, if possible, a minimal example
                - Error messages, if any
                - Expected and actual behavior
                - Information about the environment, including dagger version, OS, etc.
            - If it's a feature request:
                - What the feature is
                - Who requested it
                - Why the feature is needed
                - How the feature should work

            If you end up creating or updating an issue, always reference the issue URL in your response.
            If the repository name is not specified, use the default repository: {CONFIG.GITHUB_REPO}
            """
        ),
        mcp_servers=[github_server],
    )

def _notion_agent(notion_server: MCPServer) -> Agent[AgentContext]:
    return Agent[AgentContext](
        name="Notion Agent",
        model="gpt-4.1",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            """
            You are a helpful agent responsible for interacting with Notion.
            """
        ),
        mcp_servers=[notion_server],
    )

class SummaryOutput(BaseModel):
    title: str
    summary: str

def _summary_agent()  -> Agent[AgentContext]:
    return Agent[AgentContext](
        name="Summary Agent",
        model="gpt-4.1",
        handoff_description="An agent that can summarize a conversation",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            """
            You are a helpful agent whose goal is to summarize conversations.

            - A direct message addressed to you: this may provide further instructions on what and how to summarize
            - (Optional) reference to a message. Strong hint at what needs to be summarized.
            - Chat history: Messages prior to your invocation, where additional context should be looked for.

            Note that the history might contain unrelated messages between people.
            Your job is to find the most relevant messages to the conversation, using the direct message and reference as clues
            as to which conversation is being referred.

            You will output a nice summary along with a title for the thread. Your responses will be sent verbatim to the
            user, so speak directly to them.
            """
        ),
        output_type=SummaryOutput,
    )

def _sandbox_agent(sandbox_server: MCPServer)  -> Agent[AgentContext]:
    return Agent[AgentContext](
        name="Sandbox Agent",
        model="gpt-4.1",
        handoff_description="An agent that can execute code in an isolated sandbox",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            """
            You are a helpful agent whose goal is to execute code, provide guidance on build errors if any, and provide output.

            Use your tools to execute code.

            If the code is a snippet, wrap it in a main function and execute it. Don't forget to include any import statements.

            DO NOT EXECUTE CODE THAT MIGHT CAUSE DAMAGE TO THE SYSTEM OR TO OTHER USERS. THIS IS YOUR PRIME DIRECTIVE.
            """
        ),
        mcp_servers=[sandbox_server],
    )

class TriageOutput(BaseModel):
    title: str
    summary: str

def _main_agent(github_server: MCPServer, notion_server: MCPServer, sandbox_server: MCPServer):
    return Agent[AgentContext](
        name="Triage Agent",
        model="gpt-4.1",
        handoff_description="A triage agent that can delegate a user's request to the appropriate agent.",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            """
            You are a helpful Discord bot. You can use your tools to help answer questions and perform tasks.
            If a specialized agent better suited to the user's request is available, delegate to it.
            Your response will be sent verbatim back to the user, so speak in the appropriate tone.
            """
        ),
        # output_type=TriageOutput,
        tools = [
            _issue_agent(github_server).as_tool(
                tool_name="issue_agent",
                tool_description="agent responsible for filing issues and bug reports",
            ),
            _github_agent(github_server).as_tool(
                tool_name="github_agent",
                tool_description="generic agent to interact with GitHub (can manipulate repos, PRs, issues, commits, etc)",
            ),
            _notion_agent(notion_server).as_tool(
                tool_name="notion_agent",
                tool_description="agent responsible for interacting with Notion",
            ),
            _sandbox_agent(sandbox_server).as_tool(
                tool_name="sandbox_agent",
                tool_description="agent responsible for executing code in an isolated sandbox",
            ),
        ],
        # handoffs=[
        #     # issue_agent,
        #     # github_agent,
        # ],
    )

def _mcp_server_docker(image: str, env: dict[str, str]) -> MCPServer:
    # docker run -i --rm [-e <vars>] <image>
    args = [
        "run",
        "-i",
        "--rm",
    ]
    for key, value in env.items():
        args.extend(["-e", f"{key}={value}"])
    args.append(image)

    mcp_server = MCPServerStdio(
        params={
            "command": "docker",
            "args": args,
        }
    )
    return mcp_server

def _mcp_server_dagger(module: str) -> MCPServer:
    # dagger -m <module> mcp
    args = [
        "dagger",
        "-m",
        module,
        "mcp",
    ]
    mcp_server = MCPServerStdio(
        client_session_timeout_seconds=300,
        # params={
        #     "command": "dagger",
        #     "args": args,
        #     "env": os.environ,
        # },
        params={
            "command": "/Users/al/work/dagger/hack/with-dev",
            "args": args,
            "env": os.environ,
        },
    )
    return mcp_server

class Triager():
    def __init__(self):
        self._github_mcp_server = _mcp_server_docker(
            image="ghcr.io/github/github-mcp-server",
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": CONFIG.GITHUB_TOKEN,
            },
        )

        self._notion_mcp_server = _mcp_server_docker(
            image="mcp/notion",
            env={
                "OPENAPI_MCP_HEADERS": json.dumps({"Authorization": "Bearer " + CONFIG.NOTION_TOKEN ,"Notion-Version": "2022-06-28"}),
            },
        )

        self._sandbox_mcp_server = _mcp_server_dagger(
            module="./sandbox",
        )

        self.agent = _main_agent(
            github_server=self._github_mcp_server,
            notion_server=self._notion_mcp_server,
            sandbox_server=self._sandbox_mcp_server,
        )

    async def connect(self):
        await self._github_mcp_server.connect()
        await self._notion_mcp_server.connect()
        await self._sandbox_mcp_server.connect()

    async def cleanup(self):
        await self._github_mcp_server.cleanup()
        await self._notion_mcp_server.cleanup()
        await self._sandbox_mcp_server.cleanup()
