import pandas as pd
import plotly.graph_objects as go
import json
from google.adk.tools.tool_context import ToolContext
from google.genai.types import Part


async def create_plot(
    tool_context: ToolContext,
    data_json: str,
    series_json: str,
    x_axis: str,
    title: str,
    colors_json: str,
    y_axis_title: str,
    y2_axis_title: str,
    bar_mode: str = "group",   # "group" | "stack" | "overlay"
) -> str:
    """
    Generates a flexible plot (pie, bar, line, scatter, area) and saves it as an artifact.

    Args:
        tool_context: ADK tool context.
        data_json: JSON string of the dataset (list of dicts).
        series_json: JSON list describing each series. Example:
            [
              {"y": "sales", "type": "bar", "name": "Sales", "axis": "primary"},
              {"y": "conversion_rate", "type": "line", "name": "Conversion %", "axis": "secondary"},
              {"type": "pie", "values": "sales", "labels": "region", "name": "Sales by Region"}
            ]
        x_axis: Column name for x-axis (ignored for pie).
        title: Title of the chart.
        colors_json: JSON dict mapping series names to colors as a JSON string.
        y_axis_title: Label for the primary y-axis.
        y2_axis_title: Label for the secondary y-axis.
        bar_mode: How to display multiple bars. One of "group", "stack", "overlay".
    """

    user = tool_context._invocation_context.user_id

    try:
        # Load inputs
        df = pd.DataFrame(json.loads(data_json))
        series = json.loads(series_json)
        colors = json.loads(colors_json)

        fig = go.Figure()

        # Add traces
        for s in series:
            s_type = s.get("type", "line")
            name = s.get("name", s.get("y", "Series"))
            axis = s.get("axis", "primary")
            color = colors.get(name)

            if s_type == "line":
                fig.add_trace(go.Scatter(
                    x=df[x_axis], y=df[s["y"]], mode="lines",
                    name=name, yaxis="y2" if axis == "secondary" else "y",
                    line=dict(color=color) if color else None
                ))

            elif s_type == "scatter":
                fig.add_trace(go.Scatter(
                    x=df[x_axis], y=df[s["y"]], mode="markers",
                    name=name, yaxis="y2" if axis == "secondary" else "y",
                    marker=dict(color=color) if color else None
                ))

            elif s_type == "bar":
                fig.add_trace(go.Bar(
                    x=df[x_axis], y=df[s["y"]], name=name,
                    yaxis="y2" if axis == "secondary" else "y",
                    marker=dict(color=color) if color else None
                ))

            elif s_type == "area":
                fig.add_trace(go.Scatter(
                    x=df[x_axis], y=df[s["y"]], name=name, fill="tozeroy",
                    yaxis="y2" if axis == "secondary" else "y",
                    line=dict(color=color) if color else None
                ))

            elif s_type == "pie":
                fig.add_trace(go.Pie(
                    values=df[s["values"]],
                    labels=df[s["labels"]],
                    name=name,
                    hole=s.get("hole", 0),  # support donut if hole > 0
                    marker=dict(colors=[colors.get(val) for val in df[s["labels"]]]) if colors else None
                ))

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
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                barmode=bar_mode if bar_mode in ["group", "stack", "overlay"] else "group"
            )
        else:
            fig.update_layout(title=title)

        # Export to HTML
        html_str = fig.to_html(full_html=False, include_plotlyjs="cdn")
        html_bytes = html_str.encode("utf-8")

        # Save artifact
        plot_artifact = Part.from_bytes(data=html_bytes, mime_type="text/html")
        filename = f"{user}:{title.replace(' ', '_')}.html"
        version = await tool_context.save_artifact(filename=filename, artifact=plot_artifact)

        return f"Successfully created and saved interactive plot '{filename}' (version {version})."

    except Exception as e:
        return f"Error while creating plot: {e}"
