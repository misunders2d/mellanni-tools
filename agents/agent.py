from google.adk.agents import Agent
from agents.image_viewer import create_image_viewer_agent
from agents.gogle_search_agent import google_search_agent_tool
from .creatives_agents.smm_creator import create_creatives_agent
from .review_violation_checker import create_review_violation_checker
from .code_executor_agent import create_code_executor_agent
from .adk_expert_agent import adk_expert_tool

from data import MODEL, get_username_str


def create_root_agent():
    root_agent = Agent(
        name="mellanni_amz_agent",
        description="An agent to help with Mellanni ecommerce tasks",
        instruction= (
            "You are a helpful assistant named Jeff, with access to specific sub-agents for different tasks.\n"
            "You can delegate tasks to these sub-agents and manage their responses.\n"
            "Check the sub-agents and tools available to you and use them as needed. "
            "Generally you have abilites to search the web using google search, create and improve image and video prompts, view images."
            "Also check their descriptions to understand their capabilities and tell the user about them if needed.\n"
            f"{get_username_str()}\n"
        ),
        model=MODEL,
        sub_agents=[
            create_image_viewer_agent(),
            create_creatives_agent(),
            create_review_violation_checker(),
            adk_expert_tool()
            ],
        tools=[google_search_agent_tool(), create_code_executor_agent()]
        )
    return root_agent