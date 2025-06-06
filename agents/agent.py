from google.adk.agents import Agent
from agents.image_viewer import image_viewer_agent
from agents.gogle_search_agent import google_agent_tool
import streamlit as st

from data import MODEL

user_name = st.user.get('name', 'Unknown User')
username_str = f"The user's name is {user_name}" if user_name != 'Unknown User' else "The user's name is not available."

root_agent = Agent(
    name="mellanni_amz_agent",
    description="An agent to help with Mellanni ecommerce tasks",
    instruction=f"""
You are a helpful assistant named Jeff, with access to specific sub-agents for different tasks. You can delegate tasks to these sub-agents and manage their responses.
Check the sub-agents and tools available to you and use them as needed. Also check their descriptions to understand their capabilities and tell the user about them if needed.
{username_str}
""",
    model=MODEL,
    sub_agents=[image_viewer_agent],
    tools=[google_agent_tool])