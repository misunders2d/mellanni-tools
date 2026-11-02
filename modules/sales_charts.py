from html import escape
import re

import streamlit as st
from streamlit_echarts import JsCode, st_echarts
import pandas as pd


def render_sales_chart(
    df: pd.DataFrame,
    ads_df: pd.DataFrame,
    show_change_notes: bool = True,
    show_lds: bool = False,
    available_inv: bool = True,
    height: int = 600,
    comparison_df: pd.DataFrame | None = None,
    comparison_start=None,
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
        round(x, 1) if pd.notna(x) else None for x in df["30-day avg"].tolist()
    ]

    comparison = None
    if comparison_df is not None and comparison_start is not None:
        comparison_dates = pd.date_range(comparison_start, periods=len(dates))
        previous = pd.Series(
            comparison_df["units"].to_numpy(),
            index=pd.to_datetime(comparison_df["date"]).dt.normalize(),
        ).reindex(comparison_dates)
        comparison = [
            {"value": round(value, 1) if pd.notna(value) else None,
             "comparison_date": day.strftime("%Y-%m-%d")}
            for day, value in previous.items()
        ]

    legend_names = [
        "Units", "Unit forecast", "30-day avg", "Sessions", "Inventory", "Stockout",
        "Ad Spend", "ACoS", "Ad Units", "Impressions", "Clicks",
    ]
    if comparison is not None:
        legend_names.append("Comparison units")
    saved_selection = st.session_state.get("sales_trends_chart_legend", {})
    selected = {
        name: saved_selection.get(name, name not in ("Ad Units", "Impressions", "Clicks"))
        for name in legend_names
    }
    extra_axes = [name for name in ("Ad Units", "Impressions", "Clicks") if selected[name]]

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

            # Both the source and daily aggregation separate individual notes
            # with pipes. Commas inside a note remain part of its text.
            notes = [part.strip() for part in str(note).split(" | ") if part.strip()]
            if not show_lds:
                notes = [part for part in notes if not re.match(r"^(?:LD|BD)\b", part, re.I)]
            if not notes:
                continue
            note_str = "<br/>".join(escape(part) for part in notes)

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
            "formatter": JsCode(
                "function(ps) { if (!Array.isArray(ps)) ps = [ps]; if (!ps.length) return ''; "
                "var text = '<b>' + ps[0].axisValueLabel + '</b>'; "
                "for (var i = 0; i < ps.length; i++) { var p = ps[i]; "
                "if (p.value == null || !isFinite(Number(p.value))) continue; "
                "var label = p.seriesName; var value = Number(p.value); "
                "var display = value.toLocaleString(undefined, {maximumFractionDigits: 1}); "
                "if (label === 'Ad Spend') display = '$' + value.toFixed(2); "
                "if (label === 'ACoS' || label === 'Stockout') display += '%'; "
                "if (p.data && p.data.comparison_date) label += ' (' + p.data.comparison_date + ')'; "
                "text += '<br/>' + p.marker + ' ' + label + ': <b>' + display + '</b>'; } "
                "return text; }"
            ).js_code,
        },
        "legend": [
            {
                "data": legend_names[:6] + (["Comparison units"] if comparison is not None else []),
                "selected": selected,
                "type": "scroll", "top": "0%", "left": "2%", "width": "75%",
                "textStyle": {"color": "#555"},
            },
            {
                "data": legend_names[6:11], "selected": selected,
                "type": "scroll", "top": "68%", "left": "2%", "width": "96%",
                "textStyle": {"color": "#555"},
            },
        ],
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
            {"left": 75 + 50 * len(extra_axes), "right": 115, "top": "10%", "height": "37%"},
            # Middle Grid: Stockout (15% height)
            {"left": 75 + 50 * len(extra_axes), "right": 115, "top": "56%", "height": "10%"},
            # Bottom Grid: Ads (20% height)
            {"left": 75 + 50 * len(extra_axes), "right": 115, "top": "76%", "bottom": 55},
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
                "nameTextStyle": {"align": "right"},
                "type": "value",
                "gridIndex": 0,
                "position": "right",
                "offset": 0,
                "splitLine": {"show": False},
                "axisLine": {"show": True, "lineStyle": {"color": "#fac858"}},
            },
            {
                "name": "Inventory",
                "nameTextStyle": {"align": "left"},
                "type": "value",
                "gridIndex": 0,
                "position": "right",
                "offset": 50,
                "splitLine": {"show": False},
                "axisLine": {"show": True, "lineStyle": {"color": "#91cc75"}},
            },
            # --- Middle Grid Axis (Index 3) ---
            {
                "name": "Stockout estimate",
                "nameLocation": "start",
                "type": "value",
                "gridIndex": 1,
                "min": 0,
                "max": 100,
                "inverse": True,  # Inverted axis for hanging chart
                "splitLine": {"show": False},
                "axisLabel": {
                    "formatter": "{value} %"
                },  # Show as percentage (positive)
            },
            # --- Bottom Grid Axes (Index 4, 5) ---
            {"name": "Ad Spend ($)", "nameTextStyle": {"align": "left"},
             "type": "value", "gridIndex": 2, "inverse": False},
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
                "nameTextStyle": {"fontSize": 10},
                "position": "left",
                "type": "value",
                "show": selected["Ad Units"],
                "offset": 50 * (extra_axes.index("Ad Units") + 1) if selected["Ad Units"] else 0,
                "gridIndex": 2,
                "inverse": False,
            },
            {
                "name": "Impressions",
                "nameTextStyle": {"fontSize": 10},
                "position": "left",
                "type": "value",
                "show": selected["Impressions"],
                "offset": 50 * (extra_axes.index("Impressions") + 1) if selected["Impressions"] else 0,
                "gridIndex": 2,
                "inverse": False,
            },
            {
                "name": "Clicks",
                "nameTextStyle": {"fontSize": 10},
                "position": "left",
                "type": "value",
                "show": selected["Clicks"],
                "offset": 50 * (extra_axes.index("Clicks") + 1) if selected["Clicks"] else 0,
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

    if comparison is not None:
        option["series"].append({
            "name": "Comparison units", "type": "line", "xAxisIndex": 0, "yAxisIndex": 0,
            "data": comparison, "connectNulls": False, "showSymbol": False,
            "lineStyle": {"type": "dashed", "width": 2},
            "itemStyle": {"color": "#707785"}, "emphasis": {"focus": "series"},
        })
    changed = st_echarts(
        options=option, height=f"{height}px", key="sales_trends_echarts",
        events={"legendselectchanged": "function(params) { return params.selected; }"},
    )
    if isinstance(changed, dict):
        selection = {**selected, **{name: value for name, value in changed.items()
                                   if name in selected and isinstance(value, bool)}}
        if selection != selected:
            st.session_state["sales_trends_chart_legend"] = selection
            st.rerun()
    st.caption("Stockout is an estimate weighted by recent demand; missing inventory remains a gap.")
