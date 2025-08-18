from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

from data import SEARCH_AGENT_MODEL


def google_search_agent_tool():
    google_search_agent_tool = AgentTool(
        agent=Agent(
            name="google_search_agent",
            description="Use this agent to perform Google searches and retrieve information from the web.",
            instruction="You are an agent specialized in performing Google searches. You MUST use the `google_search` tool to find information on the web. Make sure to provide clear and specific queries to get the best results.",
            model=SEARCH_AGENT_MODEL,
            sub_agents=[],
            tools=[google_search],
        ),
        skip_summarization=True,
    )
    return google_search_agent_tool
