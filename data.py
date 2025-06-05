import os
from google.adk.models.lite_llm import LiteLlm


OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')


MODEL = LiteLlm('openai/gpt-4o-mini', api_key=OPENAI_API_KEY)
