from google.adk.agents import Agent

from data import CREATIVES_AGENT_MODEL

from . import prompts
from .sub_agents import (
    create_storyline_loop_agent, create_full_content_loop_agent, create_image_prompt_loop_agent, create_video_generator_loop_agent
)
from .tools import create_vertexai_image, read_write_google_sheet

def create_creatives_agent():
    creatives_agent = Agent(
        model=CREATIVES_AGENT_MODEL,
        # model='gemini-2.0-flash-live-preview-04-09', # for live preview - audio etc.
        name='smm_content_creator',
        description='''
        An orchestrator agent running a group of sub-agents who can create an engaging,
        fun and smm-focused content for various platforms (like TikTok, Instagram, etc.).
        Can also create images and improve image prompts, generate prompts for videos.
        ''',
        instruction=prompts.COORDINATOR_AGENT_INSTRUCTIONS,
        sub_agents=[create_storyline_loop_agent(), create_full_content_loop_agent(), create_image_prompt_loop_agent(), create_video_generator_loop_agent()],
        tools=[create_vertexai_image]
        # after_agent_callback=read_write_google_sheet
    )
    return creatives_agent