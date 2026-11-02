import streamlit as st
from streamlit_echarts import st_echarts
import pandas as pd


def render_sales_chart(
    df: pd.DataFrame,
    ads_df: pd.DataFrame,
    show_change_notes: bool = True,
    show_lds: bool = False,
    available_inv: bool = True,
    height: int = 600,
):
    """
    Renders a synchronized multi-grid ECharts visualization for Sales, Stockout, and Ads data.
    """

    # Ensure dates are strings for ECharts
    if not df.empty:
        dates = df["date"].astype(str).tolist()
    elif not ads_df.empty:
        dates = ads_df["date"].astype(str).tolist()
    else:
        st.warning("No data to display")
        return

    # --- Prepare Data Series ---
    # Main Chart Data
    # Remove fillna(0) to allow gaps (None/NaN)
    # MUST convert NaN to None for JSON serialization
    # Rounding: Units/Sessions are integers (0 decimals)
    units = [int(round(x)) if pd.notna(x) else None for x in df["units"].tolist()]
    forecast_units = [
        int(round(x)) if pd.notna(x) else None for x in df["forecast_units"].tolist()
    ]
    sessions = [int(round(x)) if pd.notna(x) else None for x in df["sessions"].tolist()]
    avg_units = [
        int(round(x)) if pd.notna(x) else None for x in df["30-day avg"].tolist()
    ]

    # Inventory Logic
    inv_col = "available" if available_inv else "inventory_supply_at_fba"
    # Fallback if column missing (though it should be there from SQL)
    if inv_col not in df.columns:
        inv_col = (
            "available" if "available" in df.columns else "inventory_supply_at_fba"
        )

    inventory = df[inv_col].tolist() if inv_col in df.columns else []
    # Inventory usually doesn't have gaps logic applied upstream?
    # Upstream 'cols_to_null' didn't include inventory. So fillna(0) is fine or keep as is.
    # But let's be safe.
    # Rounding: Inventory is integer
    inventory = [int(round(x)) if pd.notna(x) else None for x in inventory]

    # Keep unknown inventory and excluded dates as gaps, including when the
    # source has no stockout column. The sales engine supplies fractions.
    stockout_raw = pd.to_numeric(
        df.get("stockout", pd.Series(float("nan"), index=df.index))
    )
    maximum = stockout_raw.max()
    stockout_frac = (
        stockout_raw if pd.notna(maximum) and maximum > 1 else stockout_raw * 100.0
    )
    stockout_y = [round(x, 1) if pd.notna(x) else None for x in stockout_frac.tolist()]

    # Ads Chart Data
    # Ads Chart Data
    # Rounding: Ad Spend to 2 decimals, Sales to 2 decimals
    ad_spend = [
        round(x, 2) if pd.notna(x) else None for x in ads_df["ad_spend"].tolist()
    ]
    ad_sales = [
        round(x, 2) if pd.notna(x) else None for x in ads_df["total_sales"].tolist()
    ]
    ad_units = [
        round(x, 0) if pd.notna(x) else None for x in ads_df["total_units"].tolist()
    ]
    ad_clicks = [
        round(x, 0) if pd.notna(x) else None for x in ads_df["clicks"].tolist()
    ]
    ad_impressions = [
        round(x, 0) if pd.notna(x) else None for x in ads_df["impressions"].tolist()
    ]
    acos = []
    for s, sp in zip(ad_sales, ad_spend):
        if s is not None and sp is not None and s > 0:
            acos.append(round((sp / s) * 100, 1))
        else:
            acos.append(None)

    # --- Annotations (Change Notes) ---
    mark_points = []
    if show_change_notes and "change_notes" in df.columns:
        for date_str, note, unit_val in zip(dates, df["change_notes"], units):
            if pd.isna(note) or note == "":
                continue

            # Skip if value is None (gap)
            if unit_val is None:
                continue

            note_str = str(note)
            # Filter LD/BD if requested
            if not show_lds and (
                note_str.startswith("LD") or note_str.startswith("BD")
            ):
                continue

            mark_points.append(
                {
                    "coord": [date_str, unit_val],
                    "value": "!",  # Short symbol
                    "itemStyle": {"color": "#d94e5d"},
                    "tooltip": {
                        "show": True,
                        "formatter": f"{date_str}<br/>{note_str}",
                        "trigger": "item",  # Trigger on item hover
                        "triggerOn": "mousemove|click",
                        "position": "top",
                        "backgroundColor": "rgba(50,50,50,0.7)",
                        "textStyle": {"color": "#fff"},
                    },
                }
            )

    # --- ECharts Option ---
    option = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross", "label": {"backgroundColor": "#6a7985"}},
            "backgroundColor": "rgba(255, 255, 255, 0.9)",
            "textStyle": {"color": "#333"},
            "confine": True,
        },
        "legend": {
            "data": [
                "Units",
                "Unit forecast",
                "30-day avg",
                "Sessions",
                "Inventory",
                "Stockout",
                "Ad Spend",
                "ACoS",
                "Ad Units",
                "Impressions",
                "Clicks",
            ],
            "top": "0%",
            "textStyle": {"color": "#ccc"},
        },
        "toolbox": {
            "feature": {
                "dataZoom": {"yAxisIndex": "none"},
                "restore": {},
                "saveAsImage": {},
            }
        },
        "axisPointer": {"link": {"xAxisIndex": "all"}},
        "grid": [
            # Top Grid: Sales & Inventory (50% height)
            {"left": "5%", "right": "5%", "top": "8%", "height": "45%"},
            # Middle Grid: Stockout (15% height)
            {"left": "5%", "right": "5%", "top": "58%", "height": "15%"},
            # Bottom Grid: Ads (20% height)
            {"left": "5%", "right": "5%", "top": "78%", "height": "18%"},
        ],
        "xAxis": [
            # Axis 0: Top Grid
            {
                "type": "category",
                "boundaryGap": True,
                "axisLine": {"onZero": True},
                "data": dates,
                "gridIndex": 0,
                "axisLabel": {"show": False},  # Hide dates on top chart
            },
            # Axis 1: Middle Grid (Stockout)
            {
                "type": "category",
                "boundaryGap": True,
                "axisLine": {"onZero": True},
                "data": dates,
                "gridIndex": 1,
                "axisLabel": {"show": False},  # Hide dates on middle chart
                "show": True,
            },
            # Axis 2: Bottom Grid (Ads)
            {
                "type": "category",
                "boundaryGap": True,
                "axisLine": {"onZero": True},
                "data": dates,
                "gridIndex": 2,
                "position": "bottom",
            },
        ],
        "yAxis": [
            # --- Top Grid Axes (Index 0, 1, 2) ---
            {
                "name": "Units",
                "type": "value",
                "gridIndex": 0,
                "splitLine": {"show": False},
            },
            {
                "name": "Sessions",
                "type": "value",
                "gridIndex": 0,
                "position": "right",
                "offset": 0,
                "splitLine": {"show": False},
                "axisLine": {"show": True, "lineStyle": {"color": "#fac858"}},
            },
            {
                "name": "Inventory",
                "type": "value",
                "gridIndex": 0,
                "position": "right",
                "offset": 50,
                "splitLine": {"show": False},
                "axisLine": {"show": True, "lineStyle": {"color": "#91cc75"}},
            },
            # --- Middle Grid Axis (Index 3) ---
            {
                "name": "Stockout",
                "type": "value",
                "gridIndex": 1,
                "min": 0,
                "inverse": True,  # Inverted axis for hanging chart
                "splitLine": {"show": False},
                "axisLabel": {
                    "formatter": "{value} %"
                },  # Show as percentage (positive)
            },
            # --- Bottom Grid Axes (Index 4, 5) ---
            {"name": "Ad Spend ($)", "type": "value", "gridIndex": 2, "inverse": False},
            {
                "name": "ACoS (%)",
                "type": "value",
                "gridIndex": 2,
                "position": "right",
                "splitLine": {"show": False},
                "axisLabel": {"formatter": "{value} %"},
            },
            {
                "name": "Ad Units",
                "type": "value",
                "offset": 50,
                "gridIndex": 2,
                "inverse": False,
            },
            {
                "name": "Impressions",
                "type": "value",
                "hidden": True,
                "offset": -50,
                "gridIndex": 2,
                "inverse": False,
            },
            {
                "name": "Clicks",
                "type": "value",
                "offset": 50,
                "hidden": True,
                "gridIndex": 2,
                "inverse": False,
            },
        ],
        "dataZoom": [
            {
                "show": True,
                "realtime": True,
                "start": 0,
                "end": 100,
                "xAxisIndex": [0, 1, 2],
                "bottom": "0%",
            },
            {
                "type": "inside",
                "realtime": True,
                "start": 0,
                "end": 100,
                "xAxisIndex": [0, 1, 2],
            },
        ],
        "series": [
            # --- Top Grid Series ---
            {
                "name": "Units",
                "type": "bar",
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "data": units,
                "itemStyle": {"color": "#5470c6", "borderRadius": [4, 4, 0, 0]},
                "emphasis": {"focus": "series"},
                "markPoint": {
                    "data": mark_points,
                    "symbol": "pin",
                    "symbolSize": 30,
                    "label": {"show": True, "formatter": "!"},
                },
            },
            {
                "name": "Unit forecast",
                "type": "line",
                "lineStyle": {"type": "dash", "opacity": 0.5},
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "data": forecast_units,
                "itemStyle": {"color": "#ff00d4"},
                "emphasis": {"focus": "series"},
            },
            {
                "name": "30-day avg",
                "type": "line",
                "lineStyle": {"type": "dotted", "opacity": 0.5},
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "data": avg_units,
                "itemStyle": {"color": "#00d9ff"},
                "emphasis": {"focus": "series"},
            },
            {
                "name": "Sessions",
                "type": "line",
                "smooth": True,
                "xAxisIndex": 0,
                "yAxisIndex": 1,
                "data": sessions,
                "itemStyle": {"color": "#fac858"},
                "emphasis": {"focus": "series"},
            },
            {
                "name": "Inventory",
                "type": "line",
                "smooth": True,
                # "step": "start",
                "xAxisIndex": 0,
                "yAxisIndex": 2,
                "data": inventory,
                "itemStyle": {"color": "#91cc75"},
                "areaStyle": {"opacity": 0.1},
                "emphasis": {"focus": "series"},
            },
            # --- Middle Grid Series (Stockout) ---
            {
                "name": "Stockout",
                "type": "line",
                "xAxisIndex": 1,
                "yAxisIndex": 3,
                "data": stockout_y,
                "areaStyle": {"color": "rgba(255, 0, 0, 0.25)"},
                "lineStyle": {"width": 0},  # No line, just area
                "symbol": "none",
                "emphasis": {"focus": "series"},
                "itemStyle": {
                    "color": "rgba(255, 0, 0, 0.25)"
                },  # Force color for legend
            },
            # --- Bottom Grid Series ---
            {
                "name": "Ad Spend",
                "type": "bar",
                "xAxisIndex": 2,
                "yAxisIndex": 4,
                "data": ad_spend,
                "itemStyle": {"color": "#ee6666", "borderRadius": [4, 4, 0, 0]},
                "emphasis": {"focus": "series"},
            },
            {
                "name": "ACoS",
                "type": "line",
                "smooth": True,
                "xAxisIndex": 2,
                "yAxisIndex": 5,
                "data": acos,
                "itemStyle": {"color": "#73c0de"},
                "emphasis": {"focus": "series"},
            },
            {
                "name": "Ad Units",
                "type": "line",
                "smooth": True,
                "xAxisIndex": 2,
                "yAxisIndex": 6,
                "data": ad_units,
                "itemStyle": {"color": "#2400F0"},
                "emphasis": {"focus": "series"},
            },
            {
                "name": "Impressions",
                "type": "line",
                "smooth": True,
                "xAxisIndex": 2,
                "yAxisIndex": 7,
                "data": ad_impressions,
                "itemStyle": {"color": "#FF9500B5"},
                "emphasis": {"focus": "series"},
            },
            {
                "name": "Clicks",
                "type": "line",
                "smooth": True,
                "xAxisIndex": 2,
                "yAxisIndex": 8,
                "data": ad_clicks,
                "itemStyle": {"color": "#00FC2A"},
                "emphasis": {"focus": "series"},
            },
        ],
    }

    st_echarts(options=option, height=f"{height}px", key="sales_trends_echarts")
