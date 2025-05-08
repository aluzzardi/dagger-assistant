from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_tool import MCPTool


# Taken from agents.extensions.handoff_prompt (openai-agents)
RECOMMENDED_PROMPT_PREFIX = """
# System context
You are part of a multi-agent system called the Agents SDK, designed to make agent coordination and execution easy.
Agents uses two primary abstraction: **Agents** and **Handoffs**.
An agent encompasses instructions and tools and can hand off a conversation to another agent when appropriate.
Handoffs are achieved by calling a handoff function, generally named `transfer_to_<agent_name>`.
Transfers between agents are handled seamlessly in the background; do not mention or draw attention to these transfers in your conversation with the user.
"""


# class AgentContext(BaseModel):
#     message_user_name: str | None = None
#     message_user_id: int | None = None

# class TriageKindEnum(str, Enum):
#     question = 'question'
#     bug_report = 'bug_report'

# class TriageOutput(BaseModel):
#     summary: str
#     kind: TriageKindEnum

async def create_triage_agent(github_mcp_tool: MCPTool) -> LlmAgent:
    github_agent = LlmAgent(
        name="github_agent",
        description="Agent responsible to interact with GitHub (can manipulate repos, PRs, issues, commits, etc)",
        instruction=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            "You are a helpful, generic, GitHub agent. Use your tools to interact with GitHub. You may browse pull requests, commits, etc."
        ),
        tools=github_mcp_tool,
    )

    issue_agent = LlmAgent(
        name="issue_agent",
        description="Agent responsible for filing issues and bug reports",
        instruction=(
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
        tools=github_mcp_tool,
    )

    return LlmAgent(
        name="triage_agent",
        description="Triage agent that can delegate a user's request to the appropriate agent",
        instruction=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            """
            You are a helpful Discord bot. You can use your tools to help answer questions and perform tasks.
            If a specialized agent better suited to the user's request is available, delegate to it.
            Your response will be sent verbatim back to the user, so speak in the appropriate tone.
            """
        ),
        sub_agents=[
            issue_agent,
            github_agent,
        ],
    )
