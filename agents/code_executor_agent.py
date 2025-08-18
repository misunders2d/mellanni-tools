from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.code_executors import BuiltInCodeExecutor


def create_code_executor_agent():
    code_agent = AgentTool(
        Agent(
            name="code_executor_agent",
            model="gemini-2.0-flash",
            code_executor=BuiltInCodeExecutor(),
            instruction="""You are a calculator agent.
            When given a coding task, write and execute Python code to calculate the result.
            Return only the final result as plain text, without markdown or code blocks.
            """,
            description="Agent who executes Python code to perform different coding tasks.",
        ),
        skip_summarization=True,
    )
    return code_agent
