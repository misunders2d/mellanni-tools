from __future__ import annotations

from datetime import date
import html

import numpy as np
import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from modules import event_sheets
from modules import gcloud_modules as gc
from modules import restock_dashboard as rd
from modules import spapi_inventory
from modules.filter_modules import filter_dictionary


st.set_page_config(page_title="Restock", page_icon="📦", layout="wide")
# Login muted for this work-in-progress page per owner request.

st.title("📦 Restock")
st.caption(
    "Top ASINs by smart average daily sales ($). Current inventory uses SP-API MYI report when available. Lines: Available + Total FBA."
)
st.markdown(
    """
    <style>
      .restock-label {font-size:0.63rem; color:#777; line-height:1.05;}
      .restock-value {font-size:0.92rem; font-weight:750; color:#262730; line-height:1.15; white-space:nowrap;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_restock_inputs(long_term_days: int, history_days: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    days_to_pull = max(long_term_days + 90, history_days + 1)
    with gc.gcloud_connect() as client:
        sales = rd.query_dataframe(client, rd.build_sales_query(days_to_pull))
        inventory = rd.query_dataframe(client, rd.build_inventory_query(days_to_pull))
    dictionary = gc.pull_dictionary(market="US", full=False)
    return sales, inventory, dictionary


@st.cache_data(ttl=86400, show_spinner=False)
def load_sp_inventory_snapshot(
    cache_day: str,
    force_fresh: bool = False,
    force_token: str = "",
) -> tuple[pd.DataFrame, str | None, str]:
    result = spapi_inventory.request_inventory_report(force_fresh=force_fresh)
    normalized = rd.normalize_sp_inventory_report(result.data, snapshot_date=cache_day)
    current = rd.aggregate_inventory_history(normalized)
    return current, result.report_id, result.generated_at.isoformat()


@st.cache_data(ttl=3600, show_spinner=False)
def load_event_inputs() -> tuple[pd.DataFrame, pd.DataFrame, list[date]]:
    calendar = rd.normalize_event_calendar(event_sheets.read_event_calendar())
    performance = event_sheets.read_event_performance()
    event_dates = rd.expand_event_dates(calendar)
    return calendar, performance, event_dates


def selected_asins_from_dictionary(dictionary: pd.DataFrame) -> tuple[str, ...]:
    if dictionary.empty or "asin" not in dictionary.columns:
        return tuple()
    return tuple(
        sorted(
            {
                str(asin).strip()
                for asin in dictionary["asin"].dropna().astype(str).tolist()
                if str(asin).strip()
            }
        )
    )


def event_signature(calendar: pd.DataFrame, performance: pd.DataFrame) -> tuple:
    calendar_sig = tuple(
        calendar[["event_code", "start_date", "end_date"]].astype(str).itertuples(index=False, name=None)
    ) if not calendar.empty else tuple()
    performance_hash = (
        int(pd.util.hash_pandas_object(performance.astype(str), index=True).sum())
        if not performance.empty
        else 0
    )
    return (calendar_sig, tuple(performance.columns.astype(str).tolist()), tuple(performance.shape), performance_hash)


def build_restock_summary_cached(
    cache_key: tuple,
    sales: pd.DataFrame,
    inventory_history: pd.DataFrame,
    dictionary: pd.DataFrame,
    config: rd.RestockConfig,
    event_dates: list[date],
    event_calendar: pd.DataFrame,
    event_performance: pd.DataFrame,
    selected_asins: tuple[str, ...] | None,
) -> pd.DataFrame:
    cached = st.session_state.get("restock_summary_cache")
    if cached and cached.get("key") == cache_key:
        return cached["summary"].copy()

    summary = rd.build_restock_summary(
        sales,
        inventory_history,
        dictionary,
        config=config,
        event_dates=event_dates,
        event_calendar=event_calendar,
        event_performance=event_performance,
        selected_asins=selected_asins,
    )
    st.session_state.restock_summary_cache = {"key": cache_key, "summary": summary.copy()}
    return summary


def format_variant_label(row: pd.Series) -> str:
    collection = str(row.get("collection", "")).strip()
    variant_bits = [
        str(row.get("size", "")).strip(),
        str(row.get("color", "")).strip(),
    ]
    variant_bits = [bit for bit in variant_bits if bit and bit.lower() != "nan"]
    if collection and variant_bits:
        return f"{collection} ({', '.join(variant_bits)})"
    if collection:
        return collection
    return ", ".join(variant_bits)


def format_stockout(value) -> str:
    if pd.isna(value):
        return "—"
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    try:
        return pd.to_datetime(value).date().strftime("%Y-%m-%d")
    except Exception:
        return "—"


def render_card(
    row: pd.Series,
    inventory_history: pd.DataFrame,
    history_days: int,
    projection_days: int,
    event_calendar: pd.DataFrame,
    event_performance: pd.DataFrame,
) -> None:
    alert = bool(row["alert"])
    asin = str(row["asin"])
    days_left = row["days_to_stockout"]
    days_left_label = "∞" if not np.isfinite(days_left) else f"{days_left:.1f}"
    border_color = "#d71920" if alert else "#d0d7de"
    bg_color = "#fff1f1" if alert else "#ffffff"
    stockout_label = format_stockout(row["stockout_date"])
    safe_asin = html.escape(asin)
    safe_variant = html.escape(format_variant_label(row))
    safe_sub_collection = html.escape(str(row.get("sub_collection", "")))

    st.markdown(
        f"""
        <div style="border:2px solid {border_color}; background:{bg_color}; border-radius:12px; padding:10px; margin-bottom:6px;">
          <div style="font-weight:800; font-size:0.98rem; line-height:1.15; word-break:break-word;">{'🚨 ' if alert else ''}{safe_asin}</div>
          <div style="font-size:0.74rem; color:#555; line-height:1.25; min-height:2.5rem; margin-top:4px;">{safe_variant}</div>
          <div style="font-size:0.70rem; color:#777; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{safe_sub_collection}</div>
          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-top:8px;">
            <div><div class="restock-label">Avg $/day</div><div class="restock-value">${row['avg_dollars']:,.0f}</div></div>
            <div><div class="restock-label">Units/day</div><div class="restock-value">{row['avg_units']:,.1f}</div></div>
            <div><div class="restock-label">Days</div><div class="restock-value">{days_left_label}</div></div>
            <div><div class="restock-label">Available</div><div class="restock-value">{row['available']:,.0f}</div></div>
            <div><div class="restock-label">Total FBA</div><div class="restock-value">{row['fba_inventory']:,.0f}</div></div>
            <div><div class="restock-label">Out</div><div class="restock-value" style="font-size:0.78rem;">{stockout_label}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    series = rd.build_chart_series(
        asin,
        inventory_history,
        row,
        history_days=history_days,
        projection_days=projection_days,
        event_calendar=event_calendar,
        event_performance=event_performance,
    )
    opts = rd.make_inventory_chart_options(series, asin, alert=alert)
    st_echarts(opts, height="210px", key=f"restock_{asin}")
    with st.expander(f"SKUs ({int(row['sku_count'])})", expanded=False):
        st.write(row.get("skus", ""))
        st.caption(
            f"ISR: {row['isr']:.0%} long / {row['isr_short']:.0%} short · "
            f"30d projected remaining: {row['projected_inventory_30d']:,.0f}"
        )


with st.sidebar:
    st.header("Controls")
    top_n = st.number_input("Top ASINs", min_value=4, max_value=100, value=20, step=4)
    grid_columns = st.number_input("Grid columns", min_value=1, max_value=5, value=4, step=1)
    projection_days = st.number_input("Projection days", min_value=7, max_value=90, value=30, step=1)
    alert_days = st.number_input("Red alert if stockout < days", min_value=1, max_value=60, value=21, step=1)
    long_term_days = st.number_input("Long-term avg days", min_value=60, max_value=365, value=180, step=10)
    short_term_days = st.number_input("Short-term avg days", min_value=7, max_value=45, value=14, step=1)
    include_events = st.toggle("Include event days in velocity", value=False)
    red_alerts_only = st.toggle("Red alerts only (current filters)", value=False)
    refresh = st.button("Refresh all data")
    force_spapi_refresh = st.button(
        "Force fresh SP-API inventory",
        help="Requests a new Amazon MYI inventory report. If Amazon is still generating it, the app falls back safely.",
    )

if refresh:
    load_restock_inputs.clear()
    load_sp_inventory_snapshot.clear()
    load_event_inputs.clear()
    st.session_state.pop("restock_summary_cache", None)
    st.rerun()

force_token = ""
if force_spapi_refresh:
    load_sp_inventory_snapshot.clear()
    st.session_state.pop("restock_summary_cache", None)
    force_token = pd.Timestamp.utcnow().isoformat()

config = rd.RestockConfig(
    top_n=5000,
    long_term_days=int(long_term_days),
    short_term_days=int(short_term_days),
    history_days=30,
    projection_days=int(projection_days),
    alert_days=int(alert_days),
    include_events=include_events,
)

try:
    with st.spinner("Loading sales and inventory history..."):
        sales_df, raw_inventory_df, dictionary_df = load_restock_inputs(
            int(long_term_days),
            max(30, int(projection_days)),
        )
except Exception as exc:
    st.error(f"Could not load Restock data: {exc}")
    st.stop()

inventory_history = rd.aggregate_inventory_history(raw_inventory_df)
inventory_source = "BigQuery fallback"
inventory_warning = ""
sp_report_id = None
sp_generated_at = ""
try:
    with st.spinner("Loading SP-API current inventory report..."):
        sp_current_inventory, sp_report_id, sp_generated_at = load_sp_inventory_snapshot(
            date.today().isoformat(),
            force_fresh=force_spapi_refresh,
            force_token=force_token,
        )
    if not sp_current_inventory.empty:
        inventory_history = rd.apply_current_inventory_snapshot(inventory_history, sp_current_inventory)
        inventory_source = "SP-API GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA"
    else:
        inventory_warning = "SP-API inventory report returned no rows; using latest BigQuery inventory."
except Exception as exc:
    inventory_warning = f"SP-API inventory unavailable; using latest BigQuery inventory. Error: {exc}"

try:
    event_calendar, event_performance, event_dates = load_event_inputs()
    event_warning = ""
except Exception as exc:
    event_calendar = pd.DataFrame(columns=["event_code", "start_date", "end_date"])
    event_performance = pd.DataFrame()
    event_dates = []
    event_warning = f"Event calendar unavailable; velocity/projection use no event dates. Error: {exc}"

latest_inventory_date = inventory_history["date"].max() if not inventory_history.empty else None
latest_sales_date = pd.to_datetime(sales_df["date"]).dt.date.max() if not sales_df.empty else None

if inventory_warning:
    st.warning(inventory_warning)
if event_warning:
    st.warning(event_warning)

st.caption(
    f"Current inventory source: {inventory_source}"
    f"{f' · report {sp_report_id}' if sp_report_id else ''}"
    f"{f' · generated {sp_generated_at}' if sp_generated_at else ''} · "
    f"latest inventory snapshot: {latest_inventory_date} · latest sales date: {latest_sales_date} · "
    "Smart velocity uses ISR-adjusted short/long averages; event dates come from Google Sheet event_calendar."
)

st.session_state.dictionary = dictionary_df.copy()
filter_cols = st.columns([2, 1, 1, 1])
filtered_dictionary = filter_dictionary(
    coll_target=filter_cols[0],
    size_target=filter_cols[1],
    color_target=filter_cols[2],
    clear_btn_target=filter_cols[3],
)
has_dictionary_filter = bool(
    st.session_state.get("sel_col") or st.session_state.get("sel_size") or st.session_state.get("sel_color")
)
selected_asins = selected_asins_from_dictionary(filtered_dictionary) if has_dictionary_filter else None
summary_cache_key = (
    selected_asins if selected_asins is not None else ("__ALL_ASINS__",),
    int(long_term_days),
    int(short_term_days),
    int(projection_days),
    int(alert_days),
    bool(include_events),
    str(latest_inventory_date),
    str(latest_sales_date),
    event_signature(event_calendar, event_performance),
)

if selected_asins is not None and not selected_asins:
    summary = pd.DataFrame(columns=rd.SUMMARY_COLUMNS)
else:
    with st.spinner("Calculating Restock summary for selected filters..."):
        summary = build_restock_summary_cached(
            summary_cache_key,
            sales_df,
            inventory_history,
            dictionary_df,
            config=config,
            event_dates=event_dates,
            event_calendar=event_calendar,
            event_performance=event_performance,
            selected_asins=selected_asins,
        )

search = st.text_input("Secondary search (ASIN / title / SKU)", value="").strip().lower()
visible = rd.apply_summary_filters(
    summary,
    red_alerts_only=red_alerts_only,
    search=search,
).head(int(top_n))

kpi_cols = st.columns(5)
kpi_cols[0].metric("ASINs shown", f"{len(visible):,}")
kpi_cols[1].metric("Red alerts", f"{int(visible['alert'].sum()):,}")
kpi_cols[2].metric("Total FBA", f"{visible['fba_inventory'].sum():,.0f}")
kpi_cols[3].metric("Avg $/day", f"${visible['avg_dollars'].sum():,.0f}")
kpi_cols[4].metric("Avg units/day", f"{visible['avg_units'].sum():,.0f}")

with st.expander("Summary table", expanded=False):
    display = visible.copy()
    display["stockout_date"] = display["stockout_date"].apply(format_stockout)
    st.dataframe(
        display[
            [
                "asin",
                "collection",
                "sku_count",
                "size",
                "color",
                "avg_dollars",
                "avg_units",
                "available",
                "fba_inventory",
                "inbound_shipped",
                "days_to_stockout",
                "stockout_date",
                "alert",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

if visible.empty:
    st.info("No ASINs match filter.")
    st.stop()

for start in range(0, len(visible), int(grid_columns)):
    cols = st.columns(int(grid_columns))
    for col, (_, row) in zip(cols, visible.iloc[start : start + int(grid_columns)].iterrows()):
        with col:
            render_card(
                row,
                inventory_history,
                history_days=30,
                projection_days=int(projection_days),
                event_calendar=event_calendar,
                event_performance=event_performance,
            )
