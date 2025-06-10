from google.adk.agents import Agent
from agents.image_viewer import create_image_viewer_agent
from agents.gogle_search_agent import google_agent_tool
from .creatives_agents.smm_creator import create_creatives_agent

from data import MODEL, get_username_str


def create_root_agent():
    root_agent = Agent(
        name="mellanni_amz_agent",
        description="An agent to help with Mellanni ecommerce tasks",
        instruction=f"""
    You are a helpful assistant named Jeff, with access to specific sub-agents for different tasks. You can delegate tasks to these sub-agents and manage their responses.
    Check the sub-agents and tools available to you and use them as needed. Also check their descriptions to understand their capabilities and tell the user about them if needed.
    {get_username_str()}

    Tell the user that Sergey is implementing the AI agents system on the website and there can be some uncaugght errors.
    """,
        model=MODEL,
        sub_agents=[create_image_viewer_agent(), create_creatives_agent()],
        tools=[google_agent_tool]
        )
    return root_agent