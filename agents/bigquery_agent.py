from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.adk.planners import BuiltInPlanner
import uuid
from google.genai import types
import pandas as pd
from io import StringIO

from typing import Optional, Dict, Any

import re

from data import BIGQUERY_AGENT_MODEL, get_current_datetime, create_bq_agent_instruction, table_data
from .gogle_search_agent import google_search_agent_tool
from .bigquery_tools import credentials, create_plot, load_artifact_to_temp_bq

tool_config = BigQueryToolConfig(
    write_mode=WriteMode.BLOCKED, max_query_result_rows=10000
)


credentials_config = BigQueryCredentialsConfig(credentials=credentials)

# Instantiate a BigQuery toolset
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config, bigquery_tool_config=tool_config
)


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

    if tool_name in ("get_table_info", "execute_sql") and len(tables_to_check) == 0:
        return {
            "error": "Access to tables could not be identified and required immediate attention"
        }

    for table_info in tables_to_check:
        project_id = table_info["project_id"]
        dataset_id = table_info["dataset_id"]
        table_id = table_info["table_id"]

        if dataset_id in table_data and table_id in table_data[dataset_id]["tables"]:
            allowed_users = table_data[dataset_id]["tables"][table_id].get(
                "authorized_users"
            )
            if allowed_users and user not in allowed_users + superusers:
                return {
                    "error": f"User {user} does not have access to table `{project_id}.{dataset_id}.{table_id}`. Message `sergey@mellanni.com` if you need access."
                }
    return None


async def save_tool_output_to_artifact(
    tool_context: ToolContext, tool_response: dict
) -> dict:
    """
    Saves the received Bigquery tool response to artifacts. Always use this tool to present table data.

    Args:
        tool_response (dict): the tool response dict, containing "rows" - usually the response from execute_sql tool
    Returns:
        dict
    """

    user = tool_context._invocation_context.user_id
    try:
        filename = f"{user}:Table_{uuid.uuid4()}.csv"
        df = pd.DataFrame(tool_response["rows"])
        buf = StringIO()
        df.to_csv(buf, index=False)

        df_artifact = types.Part.from_bytes(
            data=buf.getvalue().encode("utf-8"), mime_type="text/csv"
        )
        await tool_context.save_artifact(filename=filename, artifact=df_artifact)
        return {
            "status":"SUCCESS",
            "message": f"The table has been presented to the user in the artifact service with the filename {filename}."
        }
    except Exception as e:
        return {"status": "FAILED", "MESSAGE":f"The following error occurred: {e}"}

    


# Agent Definition
def create_bigquery_agent():
    bigquery_agent = Agent(
        model=BIGQUERY_AGENT_MODEL,
        name="bigquery_agent",
        description=(
            "Agent to answer questions about the company's business performance (sales, inventory, payments etc)."
            "Uses BigQuery data and models and executes SQL queries and creates plots."
        ),
        instruction=create_bq_agent_instruction(),
        tools=[
            bigquery_toolset,
            google_search_agent_tool(name="bigquery_search_agent"),
            get_current_datetime,
            create_plot,
            load_artifact_to_temp_bq,
            save_tool_output_to_artifact
        ],
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=-1
            )
        ),
        before_tool_callback=before_bq_callback,
        # after_tool_callback=after_bq_callback,
    )
    return bigquery_agent
