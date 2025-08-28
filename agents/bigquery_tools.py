import pandas as pd
from google.cloud import bigquery
from modules.gcloud_modules import normalize_columns
import io
from datetime import datetime, timedelta

import tempfile
import os
import json
from google.oauth2 import service_account


import plotly.graph_objects as go
from google.adk.tools.tool_context import ToolContext
from google.genai.types import Part

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


async def create_plot(
    tool_context: ToolContext,
    data_list: list[dict],
    series_list: list[dict],
    x_axis: str,
    title: str,
    colors_dict: dict,
    y_axis_title: str,
    y2_axis_title: str,
    bar_mode: str = "group",  # "group" | "stack" | "overlay"
) -> str:
    """
    Generates a flexible plot (pie, bar, line, scatter, area) and saves it as an artifact.

    Args:
        tool_context: ADK tool context.
        data_list: list of values of the dataset (list of dicts).
        series_list: dict list describing each series. Example:
            [
              {"y": "sales", "type": "bar", "name": "Sales", "axis": "primary"},
              {"y": "conversion_rate", "type": "line", "name": "Conversion %", "axis": "secondary"},
              {"type": "pie", "values": "sales", "labels": "region", "name": "Sales by Region"}
            ]
        x_axis: Column name for x-axis (ignored for pie).
        title: Title of the chart.
        colors_dict: a dict mapping series names to colors as a JSON string.
        y_axis_title: Label for the primary y-axis.
        y2_axis_title: Label for the secondary y-axis.
        bar_mode: How to display multiple bars. One of "group", "stack", "overlay".
    """

    user = tool_context._invocation_context.user_id

    try:
        # Load inputs
        # df = pd.DataFrame(json.loads(data_json))
        # series = json.loads(series_json)
        # colors = json.loads(colors_json)

        df = pd.DataFrame(data_list)
        series = series_list
        colors = colors_dict

        fig = go.Figure()

        # Add traces
        for s in series:
            s_type = s.get("type", "line")
            name = s.get("name", s.get("y", "Series"))
            axis = s.get("axis", "primary")
            color = colors.get(name)

            if s_type == "line":
                fig.add_trace(
                    go.Scatter(
                        x=df[x_axis],
                        y=df[s["y"]],
                        mode="lines",
                        name=name,
                        yaxis="y2" if axis == "secondary" else "y",
                        line=dict(color=color) if color else None,
                    )
                )

            elif s_type == "scatter":
                fig.add_trace(
                    go.Scatter(
                        x=df[x_axis],
                        y=df[s["y"]],
                        mode="markers",
                        name=name,
                        yaxis="y2" if axis == "secondary" else "y",
                        marker=dict(color=color) if color else None,
                    )
                )

            elif s_type == "bar":
                fig.add_trace(
                    go.Bar(
                        x=df[x_axis],
                        y=df[s["y"]],
                        name=name,
                        yaxis="y2" if axis == "secondary" else "y",
                        marker=dict(color=color) if color else None,
                    )
                )

            elif s_type == "area":
                fig.add_trace(
                    go.Scatter(
                        x=df[x_axis],
                        y=df[s["y"]],
                        name=name,
                        fill="tozeroy",
                        yaxis="y2" if axis == "secondary" else "y",
                        line=dict(color=color) if color else None,
                    )
                )

            elif s_type == "pie":
                fig.add_trace(
                    go.Pie(
                        values=df[s["values"]],
                        labels=df[s["labels"]],
                        name=name,
                        hole=s.get("hole", 0),  # support donut if hole > 0
                        marker=(
                            dict(colors=[colors.get(val) for val in df[s["labels"]]])
                            if colors
                            else None
                        ),
                    )
                )

            else:
                return f"Error: Unsupported chart type '{s_type}'."

        # Layout (skip axes if only pie charts)
        has_pie = any(s.get("type") == "pie" for s in series)
        if not has_pie:
            fig.update_layout(
                title=title,
                xaxis=dict(title=x_axis),
                yaxis=dict(title=y_axis_title),
                yaxis2=dict(title=y2_axis_title, overlaying="y", side="right"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                barmode=(
                    bar_mode if bar_mode in ["group", "stack", "overlay"] else "group"
                ),
            )
        else:
            fig.update_layout(title=title)

        # Export to HTML
        html_str = fig.to_html(full_html=False, include_plotlyjs="cdn")
        html_bytes = html_str.encode("utf-8")

        # Save artifact
        plot_artifact = Part.from_bytes(data=html_bytes, mime_type="text/html")
        filename = f"{user}:{title.replace(' ', '_')}.html"
        version = await tool_context.save_artifact(
            filename=filename, artifact=plot_artifact
        )

        return f"Successfully created and saved interactive plot '{filename}' (version {version})."

    except Exception as e:
        return f"Error while creating plot: {e}"


async def load_artifact_to_temp_bq(tool_context: ToolContext, filename: str) -> str:
    """
    Upload a CSV/Excel artifact into BigQuery as a temporary table for quick file analysis
    (auto-deletes after 1 hour).
    Args:
        tool_context: ADK tool context.
        filename: file name of the file in the artifact service.

    """
    artifact = await tool_context.load_artifact(filename)
    if not artifact or not artifact.inline_data or not artifact.inline_data.data:
        return f"Artifact {filename} not found."

    data = bytes(artifact.inline_data.data)
    mime = artifact.inline_data.mime_type or ""

    if "csv" in mime or filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(data))
    elif "excel" in mime or filename.endswith((".xls", ".xlsx", ".xlsm")):
        df = pd.read_excel(io.BytesIO(data))
    else:
        return f"Unsupported artifact type: {mime}"

    df = normalize_columns(df)

    with bigquery.Client(
        credentials=credentials, project=credentials.project_id
    ) as client:
        try:
            # Create unique temp table name
            table_id = f"mellanni-project-da.auxillary_development.tmp_{filename.replace('.', '_')}_{int(datetime.now().timestamp())}"

            job = client.load_table_from_dataframe(df, table_id)
            job.result()  # wait for upload

            # Set expiration time (1 hour from now)
            table = client.get_table(table_id)
            table.expires = datetime.now() + timedelta(hours=1)
            client.update_table(table, ["expires"])
        except Exception as e:
            return f"Failed to upload file for analysis, convert it to .csv for better compatibility:\n{e}"

    return f"Uploaded `{filename}` to temporary BigQuery table `{table_id}` (expires in 1 hour)."
