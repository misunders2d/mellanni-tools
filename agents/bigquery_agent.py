from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.adk.planners import BuiltInPlanner
from google.genai import types

from typing import Optional, Dict, Any
from google.oauth2 import service_account
import tempfile

import os
import json
import re

from data import MODEL, get_current_datetime, table_data
from .gogle_search_agent import google_search_agent_tool

tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

try:
    import streamlit as st

    bigquery_service_account_info = st.secrets.get("gcp_service_account", "")
except:
    bigquery_service_account_info = json.loads(
        os.environ.get("gcp_service_account", "")
    )

# set google application credentials to use BigQuery tools
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

today = get_current_datetime().date()


def before_bq_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Checks if the user is authorized to see data in a specific table"""

    superusers = [
        "igor@mellanni.com",
        "margarita@mellanni.com",
        "masao@mellanni.com",
        "neel@mellanni.com",
    ]
    user = tool_context._invocation_context.user_id
    tool_name = tool.name

    tables_to_check = []

    query = args.get("query", "")
    if query:
        # Regex to find table names after FROM or JOIN. Handles backticks.
        found_tables = re.findall(
            r"(?:FROM|JOIN)\s+`?([\w.-]+)`?", query, re.IGNORECASE
        )
        for table_name in found_tables:
            parts = table_name.split(".")
            if len(parts) == 3:
                tables_to_check.append(
                    {
                        "project_id": parts[0],
                        "dataset_id": parts[1],
                        "table_id": parts[2],
                    }
                )
            elif len(parts) == 2:
                project_id = args.get("project_id")
                if project_id:
                    tables_to_check.append(
                        {
                            "project_id": project_id,
                            "dataset_id": parts[0],
                            "table_id": parts[1],
                        }
                    )
    else:
        project_id = args.get("project_id")
        dataset_id = args.get("dataset_id")
        table_id = args.get("table_id")
        if all([project_id, dataset_id, table_id]):
            tables_to_check.append(
                {
                    "project_id": project_id,
                    "dataset_id": dataset_id,
                    "table_id": table_id,
                }
            )

    for table_info in tables_to_check:
        project_id = table_info["project_id"]
        dataset_id = table_info["dataset_id"]
        table_id = table_info["table_id"]

        if dataset_id in table_data and table_id in table_data[dataset_id]["tables"]:
            allowed_users = table_data[dataset_id]["tables"][table_id].get(
                "authorized_users", []
            )
            if allowed_users and user not in allowed_users + superusers:
                return {
                    "error": f"User {user} does not have access to table `{project_id}.{dataset_id}.{table_id}`. Message `sergey@mellanni.com` if you need access."
                }
    return None


# Agent Definition
def create_bigquery_agent():
    bigquery_agent = Agent(
        model=MODEL,
        name="bigquery_agent",
        description=(
            "Agent to answer questions about the company's business performance (sales, inventory, payments etc)."
            "Uses BigQuery data and models and executes SQL queries."
        ),
        instruction=f"""
            You are a data science agent with access to several BigQuery tools.
            Make use of those tools to answer the user's questions.
            The main datasets you are working with are `mellanni-project-da.reports` and `mellanni-project-da.auxillary_development`.
            Today's date is {today.strftime("%YYY-%mm-dd")}.

            Here's the list and description of the company data structure in bigquery tables:\n{table_data}. Some tables may not have a description, prioritize those which have a description.

            The user might not be aware of the company data structure, ask them if they want to review any specific dataset and provide the descripton of this dataset.

            You must NEVER output simulated data without explicitly telling the user that the data is simulated.
            
            **IMPORTANT**
                The main mapping table for all products is `mellanni-project-da.auxillary_development.dictionary`
                *   This table contains the company's dictionary of all products, including their SKU, ASIN, and multiple parameters.
                *   When user asks about a "product" or "collection" - they typically refer to the "Collection" column of this table.
                *   You **MUST** always include this table in your query if the user is interested in collection / product performance.

                Date and time imperatives.
                *   Your date and time awareness is outdated, ALWAYS use `get_current_datetime` function to check for the current date and time,
                    especially when performing queries with dates.
                *   If the user is asking for the "latest" or up-to-date data - make sure to identify and understand the "date"-related columns and use them in your queries.
                
                Crucial Aggregation Principle for Time-Based Reports.
                *   Be careful when calculating "latest" summaries, make sure not to use "qualify" clause as it will mislead the user and might produce very wrong numbers. Instead, prefer to use "max date" method.
                *   When aggregating metrics (e.g., unit sales, dollar sales, sessions, ad clicks, impressions, ad spend, ad sales, # of SKUs with at least 1 sale) over a specific time period (like Prime Day events), you MUST ensure that:
                    *   Direct Summation for Core Metrics: For metrics like unit sales, dollar sales, sessions, ad clicks, impressions, ad spend, and ad sales, always perform a direct SUM() over the entire specified time period from the raw or daily-totaled data. NEVER sum pre-aggregated daily or per-ASIN totals if those pre-aggregations might lead to inflation when joined. Each metric should be calculated as an independent sum for the entire period.
                    *   True Distinct Counting: For metrics like "# of SKUs with at least 1 sale" (or any other distinct count over a period), always perform a COUNT(DISTINCT ...) operation over the entire specified time period. NEVER sum daily distinct counts, as this will result in an overcount.
                    *   Avoid Join-Induced Inflation: Be highly vigilant about how LEFT JOIN operations can inadvertently duplicate rows and inflate sums. The safest method is to perform independent aggregations for each metric within the specific time window (e.g., within subqueries or a single comprehensive pass) and then combine these already-aggregated totals.                


                Averages calculations.
                *   When calculating average daily sales (or units/revenue), please ensure the average is computed across all days in the specified period, including days where there were zero sales.
                    Treat non-selling days as having 0 units/revenue for the average calculation.
                    Avoid using "average" in your SQL queries, instead summarize relevant values and divide by the necessary number of days/records etc.
                    ALWAYS confirm with the user, how they want the averages to be calculated.

                Always check for duplicates.
                *   If you are planning to join the tables on specific columns, make sure the data in these columns is not duplicated.
                *   Duplicate values must be aggregated before joining to avoid data duplication.

                Marketplace / Country implication.
                *   If the user does not explicitly ask about a specific country, they always assume USA. Make sure to check relevant columns and their distinct values.

                Information check
                *   If the user is asking to check some table, FIRST ensure that this table exists

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
        before_tool_callback=before_bq_callback,
    )
    return bigquery_agent
