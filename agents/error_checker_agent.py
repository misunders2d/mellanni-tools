from google.adk.agents import Agent
from google.adk.tools import google_search



def event_error_analyzer_agent():
    analyzer_agent = Agent(
        name='error_analyzer_agent',
        description='Agent designed to analyze Google Agent Development Kit errors and exceptions',
        model='gemini-2.0-flash',
        instruction="""
        You are an expert in Google ADK (Agent Development Kit), specifically in analyzing errors.
        You are presented with an event and error, and your job is to look it up using `google_search` tool and explain the issue
        """,
        tools=[google_search]
    )
    return analyzer_agent
