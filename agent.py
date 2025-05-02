from agents import (
    Agent,
)
from agents.mcp import MCPServer
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from enum import Enum
from pydantic import BaseModel

class AgentContext(BaseModel):
    message_user_name: str | None = None
    message_user_id: int | None = None

class TriageKindEnum(str, Enum):
    question = 'question'
    bug_report = 'bug_report'

class TriageOutput(BaseModel):
    summary: str
    kind: TriageKindEnum

async def run_triage_agent(mcp_server: MCPServer):
    github_agent = Agent[AgentContext](
        name="GitHub Agent",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            "You are a helpful, generic, GitHub agent. Use your tools to interact with GitHub. You may browse pull requests, commits, etc."
        ),
        mcp_servers=[mcp_server],
    )

    issue_agent = Agent[AgentContext](
        name="Issue Agent",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            """
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
            """
        ),
        mcp_servers=[mcp_server],
    )

    return Agent[AgentContext](
        name="Triage Agent",
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
            issue_agent.as_tool(
                tool_name="issue_agent",
                tool_description="agent responsible for filing issues and bug reports",
            ),
            github_agent.as_tool(
                tool_name="github_agent",
                tool_description="generic agent to interact with GitHub (can manipulate repos, PRs, issues, commits, etc)",
            )
        ]
        # handoffs=[
        #     # issue_agent,
        #     # github_agent,
        # ],
    )
