import os
from google.adk.models.lite_llm import LiteLlm
import streamlit as st


OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')


MODEL = LiteLlm('openai/gpt-4o-mini', api_key=OPENAI_API_KEY)

USER_EMAIL = st.user.get('email', 'Unknown User')
USERNAME = st.user.get('name', 'Unknown User')
USERNAME_STR = f"The user's name is {USERNAME}" if USERNAME != 'Unknown User' else "The user's name is not available."
