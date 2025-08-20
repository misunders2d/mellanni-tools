import os
from google.adk.models.lite_llm import LiteLlm
import streamlit as st
from datetime import datetime


OPENAI_API_KEY = os.environ.get("OPENAI_AGENTS_API_KEY")

MODEL = "gemini-2.5-flash"
# MODEL = LiteLlm('openai/gpt-4o-mini', api_key=OPENAI_API_KEY)
SEARCH_AGENT_MODEL = "gemini-2.5-flash-lite"
CREATIVES_AGENT_MODEL = "gemini-2.5-flash"


def get_user_email():
    return st.user.get("email", "Unknown User")


# USER_EMAIL = st.user.get('email', 'Unknown User')


def get_username():
    return st.user.get("name", "Unknown User")


# USERNAME = st.user.get('name', 'Unknown User')


def get_username_str():
    return (
        f"The user's name is {get_username()}."
        if get_username() != "Unknown User"
        else "The user's name is not available."
    )


# USERNAME_STR = f"The user's name is {USERNAME}." if USERNAME != 'Unknown User' else "The user's name is not available."


def get_current_datetime():
    """A helper function used to retrieve current date and time. Use it when you need to be time-aware."""
    return datetime.now()
