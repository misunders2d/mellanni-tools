from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.oauth2 import service_account
import tempfile

import os
import json

from data import MODEL

# Define a tool configuration to block any write operations
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

# Define a credentials config - in this example we are using application default
# credentials
# https://cloud.google.com/docs/authentication/provide-credentials-adc
# application_default_credentials, _ = google.auth.default()

try:
    import streamlit as st

    bigquery_service_account_info = st.secrets.get("gcp_service_account","")
except:
    bigquery_service_account_info = json.loads(os.environ.get("gcp_service_account",""))


with tempfile.NamedTemporaryFile(
    mode="w", delete=False, suffix=".json"
) as temp_key_file:
    json.dump(dict(bigquery_service_account_info), temp_key_file)
    temp_key_file_path = temp_key_file.name
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_file_path


credentials = service_account.Credentials.from_service_account_file(temp_key_file_path)


credentials_config = BigQueryCredentialsConfig(credentials=credentials)

# Instantiate a BigQuery toolset
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config, bigquery_tool_config=tool_config
)


# Agent Definition
def create_bigquery_agent():
    bigquery_agent = Agent(
        model=MODEL,
        name="bigquery_agent",
        description=(
            "Agent to answer questions about BigQuery data and models and execute"
            " SQL queries."
        ),
        instruction="""\
            You are a data science agent with access to several BigQuery tools.
            Make use of those tools to answer the user's questions.
            The main datasets you are working with are `mellanni-project-da.reports` and `mellanni-project-da.auxillary_development`
        """,
        tools=[bigquery_toolset],
    )
    return bigquery_agent
