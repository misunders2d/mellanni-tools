from google.adk.agents import Agent
from google.adk.tools import load_web_page, agent_tool


def adk_expert_tool():
    analyzer_agent = Agent(
        name="adk_expert_agent",
        description="Agent designed to answer questions about Google Agent Development Kit and analyze Google Agent Development Kit errors and exceptions.",
        model="gemini-2.0-flash",
        instruction="""
            You are an expert in Google ADK (Agent Development Kit), specifically in analyzing errors.
            Your main source of knowledge is the official Google ADK documentation located here:
            https://google.github.io/adk-docs/
            You are presented with question related to Google ADK or with an event and error, and your job is to look it up using `load_web_page` tool with the provided link and explain the issue.
            IMPORTANT: Use the information from the official documentation to provide a detailed explanation of the error.
            """,
        tools=[load_web_page.load_web_page],
    )
    return analyzer_agent
