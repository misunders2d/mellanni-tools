import asyncio
from datetime import date, datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from reports import all_orders_report, process_reports
from streamlit_echarts import JsCode, st_echarts

from data import pantone_to_hex
from login import require_login, require_role
from modules import gcloud_modules as gc
from modules.events import event_dates_list
from modules.filter_modules import filter_dictionary
from modules.gcloud_modules import bigquery

pacific = ZoneInfo("America/Los_Angeles")
utc = ZoneInfo("UTC")
US_MARKETPLACE_ID = "ATVPDKIKX0DER"
ORDER_DIMENSION_COLUMNS = ("collection", "size", "color")

st.set_page_config(page_title="Sales hourly", page_icon="media/logo.ico", layout="wide")
require_login()

require_role("admin", "sales")

st.markdown(
    """
    <style>
    @media (max-width: 1000px) {
        [data-testid="stMetricValue"] p {
            font-size: 1.75rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


### Logic ###
@st.fragment(run_every=1)
def update_pst_time(widget):
    time_now = datetime.now(pacific)
    time_str = time_now.strftime("%Y-%m-%d %H:%M:%S")
    widget.caption(f"Pacific time:\n{time_str}")


def read_from_text(report_str: str) -> pd.DataFrame:
    """
    Dump text report to a temp file and read it with pandas into a DataFrame
    """
    data = pd.read_csv(StringIO(report_str), sep="\t")
    data["pacific_datetime"] = (
        pd.to_datetime(data["purchase-date"], utc=True)
        .dt.tz_convert(pacific)
        .dt.tz_localize(None)
    )
    data["pacific_date"] = pd.to_datetime(data["pacific_datetime"]).dt.date
    return add_order_dimensions(data)


def add_order_dimensions(data: pd.DataFrame) -> pd.DataFrame:
    """Add product dimensions required by order filters and charts."""
    missing_columns = [
        column for column in ORDER_DIMENSION_COLUMNS if column not in data.columns
    ]
    if not missing_columns:
        return data

    dictionary = gc.pull_dictionary()[["sku", *missing_columns]].copy()
    return pd.merge(data, dictionary, how="left", on="sku", validate="m:1")


async def get_orders_data(start_time: datetime, end_time: datetime):
    try:
        response = await all_orders_report(
            days=None, dataStartTime=start_time, dataEndTime=end_time
        )
    except Exception as e:
        return f"Failed to request report from Amazon SP-API: {e}"

    try:
        all_orders_text = await process_reports.check_and_download_report(
            response, time_to_wait=120
        )
    except Exception as e:
        return f"Failed to download report: {e}"

    if all_orders_text and isinstance(all_orders_text, str):
        return read_from_text(all_orders_text)
    return "Report could not be downloaded"


@st.cache_data(
    ttl=86_400,  # 24 hours
    max_entries=64, show_spinner="Pulling 30-day hourly average from BigQuery..."
)
def get_hourly_baseline(
    asins: tuple[str, ...],
    sales_channels: tuple[str, ...],
    as_of_date: str,
    event_dates: tuple[str, ...],
):
    """Return avg units by Pacific hour, excluding event dates."""
    if not asins or not sales_channels:
        return pd.DataFrame(columns=["pacific_hour", "avg_units"])

    bq_event_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in event_dates]

    query = """
        WITH date_grid AS (
            SELECT pacific_date
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(@as_of_date, INTERVAL 30 DAY),
                DATE_SUB(@as_of_date, INTERVAL 1 DAY)
            )) AS pacific_date
            WHERE pacific_date NOT IN UNNEST(@event_dates)
        ),
        hour_grid AS (
            SELECT pacific_hour
            FROM UNNEST(GENERATE_ARRAY(0, 23)) AS pacific_hour
        ),
        sales AS (
            SELECT
                DATE(purchase_date, "America/Los_Angeles") AS pacific_date,
                EXTRACT(HOUR FROM DATETIME(purchase_date, "America/Los_Angeles")) AS pacific_hour,
                SUM(quantity) AS units
            FROM `mellanni-project-da.reports.all_orders`
            WHERE DATE(purchase_date, "America/Los_Angeles") BETWEEN DATE_SUB(@as_of_date, INTERVAL 30 DAY)
                AND DATE_SUB(@as_of_date, INTERVAL 1 DAY)
                AND DATE(purchase_date, "America/Los_Angeles") NOT IN UNNEST(@event_dates)
                AND asin IN UNNEST(@asins)
                AND LOWER(sales_channel) IN UNNEST(@sales_channels)
            GROUP BY pacific_date, pacific_hour
        )
        SELECT
            h.pacific_hour,
            AVG(COALESCE(s.units, 0)) AS avg_units
        FROM date_grid d
        CROSS JOIN hour_grid h
        LEFT JOIN sales s
            ON s.pacific_date = d.pacific_date
            AND s.pacific_hour = h.pacific_hour
        GROUP BY h.pacific_hour
        ORDER BY h.pacific_hour
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("asins", "STRING", list(asins)),
            bigquery.ArrayQueryParameter(
                "sales_channels", "STRING", [c.lower() for c in sales_channels]
            ),
            bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date),
            bigquery.ArrayQueryParameter("event_dates", "DATE", bq_event_dates),
        ]
    )

    try:
        with gc.gcloud_connect() as client:
            return client.query(query, job_config=job_config).to_dataframe()
    except Exception as e:
        st.warning(f"Failed to pull 30-day hourly average from BigQuery: {e}")
        return pd.DataFrame(columns=["pacific_hour", "avg_units"])


@st.cache_data(
    ttl=86_400,  # 24 hours
    max_entries=64,
    show_spinner="Loading 30-day account hourly average...",
)
def get_account_hourly_baseline(
    as_of_date: str, event_dates: tuple[str, ...]
) -> pd.DataFrame:
    """Return account-level average units by Pacific hour for prior 30 days."""
    bq_event_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in event_dates]
    query = """
        WITH date_grid AS (
            SELECT pacific_date
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(@as_of_date, INTERVAL 30 DAY),
                DATE_SUB(@as_of_date, INTERVAL 1 DAY)
            )) AS pacific_date
            WHERE pacific_date NOT IN UNNEST(@event_dates)
        ),
        hour_grid AS (
            SELECT pacific_hour
            FROM UNNEST(GENERATE_ARRAY(0, 23)) AS pacific_hour
        ),
        sales AS (
            SELECT
                date_pt AS pacific_date,
                EXTRACT(
                    HOUR FROM DATETIME(hour_start_utc, "America/Los_Angeles")
                ) AS pacific_hour,
                SUM(COALESCE(unit_count, 0)) AS units
            FROM `mellanni-project-da.ppc_aws_stream.ppc_account_hourly`
            WHERE marketplace_id = @marketplace_id
                AND date_pt BETWEEN DATE_SUB(@as_of_date, INTERVAL 30 DAY)
                    AND DATE_SUB(@as_of_date, INTERVAL 1 DAY)
                AND date_pt NOT IN UNNEST(@event_dates)
            GROUP BY pacific_date, pacific_hour
        )
        SELECT
            h.pacific_hour,
            AVG(COALESCE(s.units, 0)) AS avg_units
        FROM date_grid d
        CROSS JOIN hour_grid h
        LEFT JOIN sales s
            ON s.pacific_date = d.pacific_date
            AND s.pacific_hour = h.pacific_hour
        GROUP BY h.pacific_hour
        ORDER BY h.pacific_hour
    """
    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=1_000_000_000,
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "marketplace_id", "STRING", US_MARKETPLACE_ID
            ),
            bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date),
            bigquery.ArrayQueryParameter("event_dates", "DATE", bq_event_dates),
        ],
    )

    with gc.gcloud_connect() as client:
        return client.query(query, job_config=job_config).to_dataframe()


@st.cache_data(
    ttl=600,
    max_entries=64,
    show_spinner="Loading near-live hourly sales and advertising...",
)
def get_hourly_overview(start_time: datetime, end_time: datetime) -> pd.DataFrame:
    """Return near-live account metrics at Pacific-hour grain."""
    query = """
        SELECT
            hour_start_utc,
            SUM(COALESCE(total_sales, 0)) AS total_sales,
            SUM(COALESCE(order_count, 0)) AS order_count,
            SUM(COALESCE(unit_count, 0)) AS unit_count,
            SUM(COALESCE(ad_spend, 0)) AS ad_spend,
            SUM(COALESCE(ad_sales, 0)) AS ad_sales,
            SUM(COALESCE(ad_purchases, 0)) AS ad_purchases,
            SUM(COALESCE(ad_units, 0)) AS ad_units,
            SUM(COALESCE(impressions, 0)) AS impressions,
            SUM(COALESCE(clicks, 0)) AS clicks
        FROM `mellanni-project-da.ppc_aws_stream.ppc_account_hourly`
        WHERE marketplace_id = @marketplace_id
            AND date_pt BETWEEN @start_date AND @end_date
            AND hour_start_utc >= @start_time
            AND hour_start_utc < @end_time
        GROUP BY hour_start_utc
        ORDER BY hour_start_utc
    """
    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=1_000_000_000,
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "marketplace_id", "STRING", US_MARKETPLACE_ID
            ),
            bigquery.ScalarQueryParameter(
                "start_date", "DATE", start_time.astimezone(pacific).date()
            ),
            bigquery.ScalarQueryParameter(
                "end_date", "DATE", end_time.astimezone(pacific).date()
            ),
            bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
            bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
        ],
    )

    with gc.gcloud_connect() as client:
        data = client.query(query, job_config=job_config).to_dataframe()

    if data.empty:
        return data

    data["pacific_datetime"] = (
        pd.to_datetime(data["hour_start_utc"], utc=True)
        .dt.tz_convert(pacific)
        .dt.tz_localize(None)
    )
    return data


def to_utc(value: date | datetime) -> datetime:
    """Interpret naive page controls as Pacific time and return UTC."""
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())
    if value.tzinfo is None:
        value = value.replace(tzinfo=pacific)
    return value.astimezone(utc)


def ceil_to_hour(value: datetime) -> datetime:
    """Return stable exclusive end time for hour-grain warehouse queries."""
    if value.minute or value.second or value.microsecond:
        return value.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return value


def safe_ratio(numerator: float, denominator: float, multiplier: float = 1) -> float:
    return numerator / denominator * multiplier if denominator else 0


def plot_hourly_overview(
    df: pd.DataFrame,
    hourly_baseline: pd.DataFrame,
    theme_type: str = "light",
):
    if df.empty:
        return

    chart_data = df.set_index("pacific_datetime").sort_index()
    full_range = pd.date_range(
        chart_data.index.min().normalize(),
        chart_data.index.max().normalize() + pd.Timedelta(hours=23),
        freq="h",
    )
    chart_data = chart_data.reindex(full_range)

    multiple_days = len(set(chart_data.index.date)) > 1
    label_format = "%b %d, %H:00" if multiple_days else "%H:00"
    labels = chart_data.index.strftime(label_format).tolist()

    def chart_values(column: str) -> list[float | None]:
        values = pd.to_numeric(chart_data[column], errors="coerce")
        return [round(float(value), 2) if pd.notna(value) else None for value in values]

    def unit_values(column: str) -> list[int | None]:
        values = pd.to_numeric(chart_data[column], errors="coerce")
        return [int(value) if pd.notna(value) else None for value in values]

    total_units = unit_values("unit_count")
    ad_units = unit_values("ad_units")
    ad_spend = chart_values("ad_spend")
    baseline_by_hour = (
        dict(
            zip(
                hourly_baseline["pacific_hour"].astype(int),
                hourly_baseline["avg_units"].astype(float),
            )
        )
        if not hourly_baseline.empty
        else {}
    )
    historical_avg_units = [
        round(baseline_by_hour.get(timestamp.hour, 0), 1)
        for timestamp in chart_data.index
    ]
    total_sales = chart_values("total_sales")
    tacos = [
        (
            round(safe_ratio(float(spend), float(sales), 100), 1)
            if spend is not None and sales not in (None, 0)
            else None
        )
        for spend, sales in zip(ad_spend, total_sales)
    ]

    is_dark = theme_type == "dark"
    colors = {
        "text": "#E5E7EB" if is_dark else "#374151",
        "muted": "#9CA3AF" if is_dark else "#6B7280",
        "grid": "#374151" if is_dark else "#E5E7EB",
        "sales": "#60A5FA" if is_dark else "#2563EB",
        "ad_units": "#FB923C" if is_dark else "#EA580C",
        "baseline": "#9CA3AF" if is_dark else "#6B7280",
        "spend": "#2DD4BF" if is_dark else "#0F766E",
        "tacos": "#F472B6" if is_dark else "#DB2777",
    }
    axis_label = {"color": colors["muted"], "fontSize": 11}
    split_line = {"lineStyle": {"color": colors["grid"], "opacity": 0.8}}
    options = {
        "backgroundColor": "transparent",
        "animation": False,
        "axisPointer": {"link": [{"xAxisIndex": "all"}]},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "line"},
            "backgroundColor": "#111827" if is_dark else "#FFFFFF",
            "borderColor": colors["grid"],
            "textStyle": {"color": colors["text"]},
        },
        "title": [
            {
                "text": "Hourly units",
                "subtext": "Current total/PPC units with prior 30-day average",
                "left": "5%",
                "top": 0,
                "textStyle": {"color": colors["text"], "fontSize": 15},
                "subtextStyle": {"color": colors["muted"], "fontSize": 11},
            },
            {
                "text": "Advertising efficiency",
                "subtext": "PPC spend and TACoS",
                "left": "5%",
                "top": "50%",
                "textStyle": {"color": colors["text"], "fontSize": 15},
                "subtextStyle": {"color": colors["muted"], "fontSize": 11},
            },
        ],
        "legend": [
            {
                "data": ["Total units", "PPC units", "30-day hourly avg"],
                "top": "2%",
                "right": "5%",
                "textStyle": {"color": colors["text"]},
            },
            {
                "data": ["PPC spend", "TACoS"],
                "top": "52%",
                "right": "5%",
                "textStyle": {"color": colors["text"]},
            },
        ],
        "grid": [
            {
                "left": "5%",
                "right": "5%",
                "top": "13%",
                "height": "28%",
                "containLabel": True,
            },
            {
                "left": "5%",
                "right": "5%",
                "top": "63%",
                "height": "25%",
                "containLabel": True,
            },
        ],
        "xAxis": [
            {
                "type": "category",
                "gridIndex": 0,
                "data": labels,
                "axisLabel": {"show": False},
                "axisTick": {"show": False},
                "axisLine": {"lineStyle": {"color": colors["grid"]}},
            },
            {
                "type": "category",
                "gridIndex": 1,
                "data": labels,
                "axisLabel": {**axis_label, "rotate": 45},
                "axisTick": {"alignWithLabel": True},
                "axisLine": {"lineStyle": {"color": colors["grid"]}},
            },
        ],
        "yAxis": [
            {
                "type": "value",
                "gridIndex": 0,
                "name": "Units",
                "nameTextStyle": {"color": colors["muted"]},
                "axisLabel": axis_label,
                "splitLine": split_line,
            },
            {
                "type": "value",
                "gridIndex": 1,
                "name": "Spend (USD)",
                "nameTextStyle": {"color": colors["muted"]},
                "axisLabel": {**axis_label, "formatter": "${value}"},
                "splitLine": split_line,
            },
            {
                "type": "value",
                "gridIndex": 1,
                "name": "TACoS",
                "position": "right",
                "nameTextStyle": {"color": colors["muted"]},
                "axisLabel": {**axis_label, "formatter": "{value}%"},
                "splitLine": {"show": False},
            },
        ],
        "series": [
            {
                "name": "30-day hourly avg",
                "type": "line",
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "smooth": False,
                "symbol": "none",
                "data": historical_avg_units,
                "z": 0,
                "lineStyle": {
                    "width": 2,
                    "type": "dashed",
                    "color": colors["baseline"],
                },
                "itemStyle": {"color": colors["baseline"]},
                "areaStyle": {"color": colors["baseline"], "opacity": 0.08},
            },
            {
                "name": "Total units",
                "type": "bar",
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "data": total_units,
                "z": 2,
                "barMaxWidth": 32,
                "itemStyle": {
                    "color": colors["sales"],
                    "borderRadius": [3, 3, 0, 0],
                    "opacity": 0.85,
                },
            },
            {
                "name": "PPC units",
                "type": "line",
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "smooth": False,
                "symbol": "none",
                "data": ad_units,
                "z": 3,
                "lineStyle": {"width": 2, "color": colors["ad_units"]},
                "itemStyle": {"color": colors["ad_units"]},
            },
            {
                "name": "PPC spend",
                "type": "bar",
                "xAxisIndex": 1,
                "yAxisIndex": 1,
                "data": ad_spend,
                "barMaxWidth": 32,
                "itemStyle": {
                    "color": colors["spend"],
                    "borderRadius": [3, 3, 0, 0],
                    "opacity": 0.85,
                },
            },
            {
                "name": "TACoS",
                "type": "line",
                "xAxisIndex": 1,
                "yAxisIndex": 2,
                "smooth": False,
                "symbol": "circle",
                "symbolSize": 4,
                "data": tacos,
                "lineStyle": {"width": 2, "color": colors["tacos"]},
                "itemStyle": {"color": colors["tacos"]},
            },
        ],
    }
    st_echarts(
        options=options,
        theme="dark" if is_dark else "",
        height="640px",
        key="hourly-account-overview",
    )


def analyze_orders(full_data: pd.DataFrame):
    top_skus = (
        full_data.groupby("sku")
        .agg({"quantity": "sum"})
        .reset_index()
        .sort_values("quantity", ascending=False)
    )
    try:
        top_skus = pd.merge(
            top_skus,
            st.session_state.dictionary[["sku", "asin"]],
            how="left",
            on="sku",
            validate="1:1",
        )
    except pd.errors.MergeError as e:
        st.error(f"Data integrity issue: duplicate SKUs detected in dictionary. {e}")
        return top_skus, pd.DataFrame(), pd.DataFrame()
    top_skus["sku"] = (
        "https://www.amazon.com/dp/" + top_skus["asin"] + "#" + top_skus["sku"]
    )
    del top_skus["asin"]

    top_orders = (
        full_data.groupby("amazon-order-id")
        .agg(
            {
                "quantity": "sum",
                "order-status": lambda x: ", ".join(x.unique()),
                "is-business-order": "first",
            }
        )
        .reset_index()
        .sort_values("quantity", ascending=False)
    )
    top_orders["amazon-order-id"] = (
        "https://sellercentral.amazon.com/orders-v3/order/"
        + top_orders["amazon-order-id"]
    )

    top_promos = (
        full_data.groupby("promotion-ids")
        .agg({"item-promotion-discount": "sum", "quantity": "sum"})
        .reset_index()
        .sort_values("quantity", ascending=False)
    )
    return top_skus, top_orders, top_promos


def set_selected_time_window(clear_order_details: bool):
    selected_option = st.session_state.time_options
    time_now = datetime.now(pacific).replace(tzinfo=None)
    match selected_option:
        case "Today":
            st.session_state.start_time = datetime.combine(
                time_now.date(), datetime.min.time()
            )
            st.session_state.end_time = time_now

        case "Yesterday":
            yesterday = time_now.date() - timedelta(days=1)
            st.session_state.start_time = datetime.combine(
                yesterday, datetime.min.time()
            )
            st.session_state.end_time = datetime.combine(
                time_now.date(), datetime.min.time()
            )

        case "Last 3 days":
            st.session_state.start_time = datetime.combine(
                time_now.date() - timedelta(days=3), datetime.min.time()
            )
            st.session_state.end_time = datetime.combine(
                time_now.date(), datetime.min.time()
            )
        case "Last 7 days":
            st.session_state.start_time = datetime.combine(
                time_now.date() - timedelta(days=7), datetime.min.time()
            )
            st.session_state.end_time = datetime.combine(
                time_now.date(), datetime.min.time()
            )
        case "Last week":
            today = time_now.weekday() + 1
            sunday = (time_now - timedelta(days=today)).date()
            prev_sunday = sunday - timedelta(days=7)
            st.session_state.start_time = datetime.combine(
                prev_sunday, datetime.min.time()
            )
            st.session_state.end_time = datetime.combine(
                sunday, datetime.min.time()
            )
    if clear_order_details:
        st.session_state.pop("hourly_report", None)


def apply_options():
    set_selected_time_window(clear_order_details=True)


def refresh_selected_time_window():
    set_selected_time_window(clear_order_details=False)


def get_selected_asins(filtered_dict: pd.DataFrame) -> tuple[str, ...]:
    return tuple(
        sorted(
            asin
            for asin in filtered_dict["asin"].dropna().astype(str).unique().tolist()
            if asin
        )
    )


def normalize_sales_channels(sales_channels) -> tuple[str, ...]:
    return tuple(
        sorted({str(channel).strip().lower() for channel in sales_channels if channel})
    )


def normalize_event_dates(events) -> tuple[str, ...]:
    normalized = set()
    for event_date in events or []:
        if event_date is None:
            continue
        if isinstance(event_date, datetime):
            normalized.add(event_date.date().isoformat())
        elif isinstance(event_date, date):
            normalized.add(event_date.isoformat())
        else:
            normalized.add(pd.to_datetime(event_date).date().isoformat())
    return tuple(sorted(normalized))


def plot_baseline_chart(hourly_baseline: pd.DataFrame):
    if hourly_baseline.empty:
        return

    baseline_by_hour = dict(
        zip(
            hourly_baseline["pacific_hour"].astype(int),
            hourly_baseline["avg_units"].astype(float),
        )
    )
    x_axis_labels = [f"{hour:02d}:00" for hour in range(24)]
    baseline_values = [round(baseline_by_hour.get(hour, 0), 1) for hour in range(24)]
    options = {
        "backgroundColor": "transparent",
        "title": {
            "text": "Last 30 days average hourly units "
            "(excluding today, current filters)",
            "left": "center",
            "textStyle": {"color": "#CDD6F4"},
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": "{b}: <b>{c} avg units</b>",
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "15%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": x_axis_labels,
            "axisLabel": {"rotate": 45, "color": "#BAC2DE"},
        },
        "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#313244"}}},
        "series": [
            {
                "name": "30-day avg hourly total",
                "type": "line",
                "smooth": True,
                "symbol": "circle",
                "lineStyle": {"width": 3, "type": "dashed", "color": "#f5e0dc"},
                "areaStyle": {"opacity": 0.08, "color": "#f5e0dc"},
                "data": baseline_values,
            }
        ],
        "color": ["#f5e0dc"],
    }
    with chart_area:
        st_echarts(options=options, height="450px")


def plot_chart(df: pd.DataFrame, hourly_baseline: pd.DataFrame | None = None):
    if len(df) == 0:
        if hourly_baseline is not None:
            plot_baseline_chart(hourly_baseline)
        return
    coll_df = (
        df.groupby("collection")
        .agg({"quantity": "sum"})
        .reset_index()
        .sort_values("quantity", ascending=False)
    )
    size_df = (
        df.groupby("size")
        .agg({"quantity": "sum"})
        .reset_index()
        .sort_values("quantity", ascending=False)
    )
    color_df = (
        df.groupby("color")
        .agg({"quantity": "sum"})
        .reset_index()
        .sort_values("quantity", ascending=False)
    )

    def get_bedsheet_hex(color_name):
        name = str(color_name).title().strip()

        # Return mapped color or Catppuccin Mocha surface gray as fallback
        return pantone_to_hex.get(name, "#585b70")

    def get_pie_options(data_df, name_col, title, is_color_chart=False):
        chart_data = []
        for _, row in data_df.iterrows():
            item = {"value": float(row["quantity"]), "name": str(row[name_col])}
            # If it's the color chart, override the item's color specifically
            if is_color_chart:
                item["itemStyle"] = {"color": get_bedsheet_hex(row[name_col])}
            chart_data.append(item)

        return {
            "title": {
                "text": title,
                "left": "center",
                "textStyle": {"color": "#CDD6F4"},
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "<b>{b}</b>: {c} units",
            },
            "series": [
                {
                    "type": "pie",
                    "radius": ["45%", "70%"],
                    "itemStyle": {
                        "borderRadius": 8,
                        "borderColor": "#1e1e2e",
                        "borderWidth": 2,
                    },
                    "label": {"show": False},
                    "emphasis": {
                        "label": {"show": True, "fontSize": "15", "fontWeight": "bold"}
                    },
                    "data": chart_data,
                }
            ],
            # Global palette used only for non-color charts
            "color": ["#89b4fa", "#fab387", "#a6e3a1", "#f38ba8", "#cba6f7", "#94e2d5"],
        }

    pie_col1, pie_col2, pie_col3 = add_chart_area.columns(3)

    with pie_col1:
        st_echarts(
            get_pie_options(coll_df, "collection", "By Collection"), height="300px"
        )
    with pie_col2:
        st_echarts(get_pie_options(size_df, "size", "By Size"), height="300px")
    with pie_col3:
        st_echarts(
            get_pie_options(color_df, "color", "By Color", is_color_chart=True),
            height="300px",
        )

    resampled = (
        df.set_index("pacific_datetime")
        .groupby("collection")["quantity"]
        .resample("h")
        .sum()
        .unstack(0)
        .fillna(0)
    )

    start_time = resampled.index.min().normalize()
    end_time = resampled.index.max().normalize() + pd.Timedelta(hours=23)
    full_range = pd.date_range(start_time, end_time, freq="h")

    resampled = resampled.reindex(full_range, fill_value=0)

    sorted_cols = resampled.sum().sort_values(ascending=False).index
    resampled = resampled[sorted_cols]

    x_axis_labels = resampled.index.strftime("%b %d, %H:00").tolist()
    hourly_totals = resampled.sum(axis=1).tolist()
    series = []

    # Catppuccin Mocha Palette
    colors = [
        "#89b4fa",
        "#fab387",
        "#a6e3a1",
        "#f38ba8",
        "#cba6f7",
        "#94e2d5",
        "#f9e2af",
    ]

    for _, col in enumerate(resampled.columns):
        col_values = resampled[col].tolist()
        series.append(
            {
                "name": str(col),
                "type": "bar",
                "stack": "total",
                "emphasis": {"focus": "series"},
                "data": [
                    {"value": v, "total": t}
                    for v, t in zip(col_values, hourly_totals)
                ],
                "itemStyle": {"borderRadius": [2, 2, 0, 0]},
            }
        )

    if hourly_baseline is not None and not hourly_baseline.empty:
        baseline_by_hour = dict(
            zip(
                hourly_baseline["pacific_hour"].astype(int),
                hourly_baseline["avg_units"].astype(float),
            )
        )
        baseline_values = [
            round(baseline_by_hour.get(ts.hour, 0), 1) for ts in resampled.index
        ]
        series.append(
            {
                "name": "30-day avg hourly total",
                "type": "line",
                "symbol": "none",
                "smooth": True,
                "z": 10,
                "lineStyle": {"width": 3, "type": "dashed", "color": "#f5e0dc"},
                "data": [
                    {"value": v, "total": t}
                    for v, t in zip(baseline_values, hourly_totals)
                ],
            }
        )

    options = {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "item",
            "formatter": JsCode("function(params) { return '<b>' + params.seriesName + '</b><br/>' + params.name + ': <b>' + params.value + ' units</b><br/>Hour total: <b>' + params.data.total + ' units</b>'; }").js_code,
        },
        "legend": {"textStyle": {"color": "#CDD6F4"}, "type": "scroll", "top": "top"},
        "grid": {"left": "3%", "right": "4%", "bottom": "15%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": x_axis_labels,
            "axisLabel": {"rotate": 45, "color": "#BAC2DE"},
        },
        "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#313244"}}},
        "series": series,
        "color": colors + ["#f5e0dc"],
    }
    with chart_area:
        st_echarts(options=options, height="550px")


### Layout ###
if "start_time" not in st.session_state:
    time_now = datetime.now(pacific).replace(tzinfo=None)
    st.session_state.start_time = datetime.combine(
        time_now.date(), datetime.min.time()
    )
    st.session_state.end_time = time_now

detail_button_name = (
    "Reload order details"
    if "hourly_report" in st.session_state
    else "Load order details"
)

start_time_col, end_time_col, time_options_col = st.columns(
    [1, 1, 1], vertical_alignment="bottom"
)
refresh_col, detail_button_col, curr_time_col = st.columns(
    [2, 2, 3], vertical_alignment="bottom"
)

start_time = start_time_col.datetime_input(
    label="Start time (Pacific)", key="start_time", disabled=True
)
end_time = end_time_col.datetime_input(
    label="End time (Pacific)", key="end_time", disabled=True
)
time_options = time_options_col.selectbox(
    label="Quick Select Timeframe",
    options=[
        # "Custom",
        "Today",
        "Yesterday",
        "Last 3 days",
        # "Last 7 days",
        # "Last week"
    ],
    index=0,
    on_change=apply_options,
    key="time_options",
    disabled=False,
)

refresh_overview = refresh_col.button(
    "Refresh overview",
    on_click=refresh_selected_time_window,
    use_container_width=True,
)
load_order_details = detail_button_col.button(
    detail_button_name,
    on_click=refresh_selected_time_window,
    type="primary",
    use_container_width=True,
)
with curr_time_col:
    time_slot = st.empty()
update_pst_time(time_slot)

if refresh_overview:
    get_hourly_overview.clear()

if load_order_details:
    if (end_time - start_time).days > 8:
        st.warning("Too long period, use Sales Trends dashboard instead")
    else:
        with st.spinner("Loading order details from Amazon SP-API..."):
            st.session_state.hourly_report = asyncio.run(
                get_orders_data(
                    start_time=to_utc(start_time),
                    end_time=to_utc(end_time),
                )
            )

st.subheader("Near-live hourly overview")
st.caption(
    "Account-level US marketplace data from BigQuery. Current hour is partial; "
    "PPC units, sales, ACoS, ROAS, and TACoS are provisional."
)

overview_data = pd.DataFrame()
overview_baseline = pd.DataFrame(columns=["pacific_hour", "avg_units"])
try:
    overview_data = get_hourly_overview(
        to_utc(start_time), ceil_to_hour(to_utc(end_time))
    )
except Exception as e:
    st.warning(f"Near-live overview could not be loaded: {e}")

if not overview_data.empty:
    try:
        overview_baseline = get_account_hourly_baseline(
            pd.to_datetime(start_time).date().isoformat(),
            normalize_event_dates(event_dates_list),
        )
    except Exception as e:
        st.warning(f"Historical hourly average could not be loaded: {e}")

if overview_data.empty:
    st.info(
        "No near-live aggregate data is available for this period. "
        "Order details can still be loaded on demand."
    )
else:
    total_sales = float(pd.to_numeric(overview_data["total_sales"]).sum())
    total_orders = int(pd.to_numeric(overview_data["order_count"]).sum())
    total_units = int(pd.to_numeric(overview_data["unit_count"]).sum())
    average_order_value = safe_ratio(total_sales, total_orders)
    total_ad_spend = float(pd.to_numeric(overview_data["ad_spend"]).sum())
    total_ad_sales = float(pd.to_numeric(overview_data["ad_sales"]).sum())
    total_ad_purchases = int(pd.to_numeric(overview_data["ad_purchases"]).sum())
    total_impressions = int(pd.to_numeric(overview_data["impressions"]).sum())
    total_clicks = int(pd.to_numeric(overview_data["clicks"]).sum())
    ctr_text = (
        f"{safe_ratio(total_clicks, total_impressions, 100):,.2f}%"
        if total_impressions
        else "—"
    )
    ppc_conversion_text = (
        f"{safe_ratio(total_ad_purchases, total_clicks, 100):,.1f}%"
        if total_clicks
        else "—"
    )

    overview_metrics_1 = st.columns([2.4, 1, 1.1, 1.3, 1.1], gap="small")
    overview_metrics_1[0].metric(
        "Total sales", f"${total_sales:,.2f}", border=True
    )
    overview_metrics_1[1].metric("Orders", f"{total_orders:,}", border=True)
    overview_metrics_1[2].metric("Units", f"{total_units:,}", border=True)
    overview_metrics_1[3].metric(
        "AOV",
        f"${average_order_value:,.2f}" if total_orders else "—",
        help="Average order value",
        border=True,
    )
    overview_metrics_1[4].metric(
        "TACoS",
        f"{safe_ratio(total_ad_spend, total_sales, 100):,.1f}%"
        if total_sales
        else "—",
        border=True,
    )

    overview_metrics_2 = st.columns([1.3, 1.3, 1.2, 1], gap="small")
    overview_metrics_2[0].metric(
        "PPC spend", f"${total_ad_spend:,.2f}", border=True
    )
    overview_metrics_2[1].metric(
        "PPC sales", f"${total_ad_sales:,.2f}", border=True
    )
    overview_metrics_2[2].metric(
        "ACoS",
        f"{safe_ratio(total_ad_spend, total_ad_sales, 100):,.1f}%"
        if total_ad_sales
        else "—",
        border=True,
    )
    overview_metrics_2[3].metric(
        "ROAS",
        f"{safe_ratio(total_ad_sales, total_ad_spend):,.2f}"
        if total_ad_spend
        else "—",
        border=True,
    )

    latest_hour = overview_data["pacific_datetime"].max().strftime(
        "%b %d, %Y %H:00 PT"
    )
    st.caption(
        f"PPC data through {latest_hour} · Selected period totals: "
        f"{total_impressions:,} impressions · {total_clicks:,} clicks · "
        f"CTR {ctr_text} · PPC CVR {ppc_conversion_text}"
    )
    plot_hourly_overview(
        df=overview_data,
        hourly_baseline=overview_baseline,
        theme_type=st.context.theme.type or "light",
    )

st.divider()
st.subheader("Order details")
st.caption(
    "Optional live SP-API report. Load only when SKU, collection, order, "
    "cancellation, or promotion detail is needed."
)

if "hourly_report" in st.session_state:
    if isinstance(st.session_state.hourly_report, pd.DataFrame):
        st.session_state.hourly_report = add_order_dimensions(
            st.session_state.hourly_report
        )
        coll_select, size_select, color_select, sales_channel_select = st.columns(
            [2, 1, 2, 2]
        )
        filtered_dict: pd.DataFrame = filter_dictionary(
            coll_target=coll_select, size_target=size_select, color_target=color_select
        )
        selected_asins = get_selected_asins(filtered_dict)
        sales_channels = (
            st.session_state.hourly_report["sales-channel"].unique().tolist()
        )
        sales_channel = sales_channel_select.multiselect(
            label="Sales channel",
            options=sales_channels,
            default=(
                ["Amazon.com"] if "Amazon.com" in sales_channels else sales_channels
            ),
        )
        report_filtered = st.session_state.hourly_report.copy()
        selected_channels = normalize_sales_channels(sales_channel)
        report_filtered = report_filtered.loc[
            (report_filtered["asin"].isin(selected_asins))
            & (report_filtered["sales-channel"].isin(sales_channel))
        ]

        baseline_as_of_date = str(datetime.now(pacific).date())
        event_dates_key = normalize_event_dates(event_dates_list)
        hourly_baseline = get_hourly_baseline(
            selected_asins, selected_channels, baseline_as_of_date, event_dates_key
        )
        metric_area = st.container()
        chart_area = st.container()
        add_chart_area = st.container()
        plot_chart(report_filtered, hourly_baseline)

        total_units = report_filtered.quantity.sum()
        total_revenue = report_filtered["item-price"].sum()
        average_price = total_revenue / total_units if total_units > 0 else 0
        cancelled_orders = len(
            report_filtered[report_filtered["order-status"].str.lower() == "cancelled"][
                "amazon-order-id"
            ].unique()
        )
        total_orders = (
            len(report_filtered["amazon-order-id"].unique()) - cancelled_orders
        )
        aov = total_revenue / total_orders if total_orders > 0 else 0

        (
            unit_metric,
            order_metric,
            dollar_metric,
            price_metric,
            aov_metric,
            cancelled_metric,
        ) = metric_area.columns([1, 1, 1, 1, 1, 1])
        unit_metric.metric(label="Units", value=total_units, format="localized")
        order_metric.metric(label="Orders", value=total_orders)
        dollar_metric.metric(label="Revenue", value=total_revenue, format="dollar")
        price_metric.metric(label="Average price", value=average_price, format="dollar")
        aov_metric.metric(label="AOV", value=aov, format="dollar")
        cancelled_metric.metric(
            label="Cancelled orders", value=cancelled_orders, format="localized"
        )

        with st.expander("Raw data"):
            total_df_area = st.container()
            analysis_df_area = st.container()
            sku_df_area, order_df_area, promo_df_area = analysis_df_area.columns(
                [1, 1, 1]
            )
            total_df_area.caption("Raw order data")
            total_df_area.dataframe(report_filtered, hide_index=True)
            top_skus, top_orders, top_promos = analyze_orders(report_filtered)
            sku_df_area.caption("Top SKUs")
            sku_df_area.dataframe(
                top_skus,
                hide_index=True,
                column_config={
                    "sku": st.column_config.LinkColumn(display_text=r"#(.*)")
                },
            )
            order_df_area.caption("Top orders")
            order_df_area.dataframe(
                top_orders,
                hide_index=True,
                column_config={
                    "amazon-order-id": st.column_config.LinkColumn(
                        display_text=r"order/(.*)",
                    )
                },
            )
            promo_df_area.caption("Top promos")
            promo_df_area.dataframe(top_promos, hide_index=True)
    else:
        st.warning(st.session_state.hourly_report)
else:
    st.info(
        "Order details are not loaded. Use **Load order details** above when "
        "product or order-level analysis is needed."
    )
