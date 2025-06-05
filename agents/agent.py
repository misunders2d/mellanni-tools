from google.adk.agents import Agent
from agents.image_viewer import image_viewer_agent

from data import MODEL

root_agent = Agent(
    name="mellanni_amz_agent",
    description="An agent to help with Mellanni Amazon store tasks. Your name is Jeff",
    instruction='You are a helpful assistant named Jeff, with access to specific sub-agents for different tasks. You can delegate tasks to these sub-agents and manage their responses.',
    model=MODEL,
    sub_agents=[image_viewer_agent],
    tools=[])