from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.adk.planners import BuiltInPlanner
from google.genai import types

from google.oauth2 import service_account
import tempfile

import os
import json

from data import MODEL, get_current_datetime
from .gogle_search_agent import google_search_agent_tool

# Define a tool configuration to block any write operations
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

# Define a credentials config - in this example we are using application default
# credentials
# https://cloud.google.com/docs/authentication/provide-credentials-adc
# application_default_credentials, _ = google.auth.default()

try:
    import streamlit as st

    bigquery_service_account_info = st.secrets.get("gcp_service_account", "")
except:
    bigquery_service_account_info = json.loads(
        os.environ.get("gcp_service_account", "")
    )


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
            "Agent to answer questions about the company's business performance (sales, inventory, payments etc)."
            "Uses BigQuery data and models and executes SQL queries."
        ),
        instruction="""\
            You are a data science agent with access to several BigQuery tools.
            Make use of those tools to answer the user's questions.
            The main datasets you are working with are `mellanni-project-da.reports` and `mellanni-project-da.auxillary_development`.
            You must NEVER output simulated data without explicitly telling the user that the data is simulated.
            
            **IMPORTANT**
                The main mapping table for all products is `mellanni-project-da.auxillary_development.dictionary`
                *   This table contains the company's dictionary of all products, including their SKU, ASIN, and multiple parameters.
                *   When user asks about a "product" or "collection" - they typically refer to the "Collection" column of this table.
                *   You **MUST** always include this table in your query if the user is interested in collection / product performance.

                Date and time implications.
                *   Your date and time awareness is outdated, ALWAYS use `get_current_datetime` function to check for the current date and time,
                    especially when performing queries with dates.
                
                Always check for duplicates.
                *   If you are planning to join the tables on specific columns, make sure the data in these columns is not duplicated.
                *   Duplicate values must be aggregated before joining to avoid data duplication.

                Marketplace / Country implication.
                *   If the user does not explicitly ask about a specific country, they always assume USA. Make sure to check relevant columns and their distinct values.

                Date and time
                *   If the user is asking for the "latest" or up-to-date data - make sure to identify and understand the "date"-related columns and use them in your queries.
                
                Test
        """,
        tools=[
            bigquery_toolset,
            google_search_agent_tool(name="bigquery_search_agent"),
            get_current_datetime,
        ],
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=-1
            )
        ),
    )
    return bigquery_agent
