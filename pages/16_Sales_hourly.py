import asyncio
from datetime import datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from reports import all_orders_report, process_reports
from streamlit_echarts import st_echarts

from data import pantone_to_hex
from login import require_login, sales_users
from modules.filter_modules import filter_dictionary

pacific = ZoneInfo("America/Los_Angeles")
utc = ZoneInfo("UTC")

st.set_page_config(page_title="Sales hourly", page_icon="media/logo.ico", layout="wide")
require_login()

if st.user.email not in sales_users:
    st.toast(
        f"User {st.user.email} does not have access to sales data. Contact Sergey for details"
    )
    st.stop()


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
    if "dictionary" in st.session_state:
        dictionary = st.session_state.dictionary[
            ["sku", "collection", "size", "color"]
        ].copy()
        data = pd.merge(data, dictionary, how="left", on="sku", validate="m:1")
    return data


async def get_orders_data(start_time: datetime, end_time: datetime):
    response = await all_orders_report(
        days=None, dataStartTime=start_time, dataEndTime=end_time
    )
    all_orders_text = await process_reports.check_and_download_report(
        response, time_to_wait=120
    )
    if all_orders_text and isinstance(all_orders_text, str):
        return read_from_text(all_orders_text)
    return "Report could not be downloaded"


def analyze_orders(full_data: pd.DataFrame):
    top_skus = (
        full_data.groupby("sku")
        .agg({"quantity": "sum"})
        .reset_index()
        .sort_values("quantity", ascending=False)
    )
    top_skus = pd.merge(
        top_skus,
        st.session_state.dictionary[["sku", "asin"]],
        how="left",
        on="sku",
        validate="1:m",
    )
    top_skus["sku"] = (
        "https://www.amazon.com/dp/" + top_skus["asin"] + "#" + top_skus["sku"]
    )
    del top_skus["asin"]

    top_orders = (
        full_data.groupby("amazon-order-id")
        .agg({"quantity": "sum", "order-status": lambda x: ", ".join(x.unique())})
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


def apply_options():
    selected_option = st.session_state.time_options
    match selected_option:
        case "Today":
            st.session_state.start_time = (datetime.now(pacific)).date()
            st.session_state.end_time = datetime.now(pacific)

        case "Yesterday":
            st.session_state.start_time = (
                datetime.now(pacific) - timedelta(days=1)
            ).date()
            st.session_state.end_time = (datetime.now(pacific)).date()

        case "Last 3 days":
            st.session_state.start_time = (
                datetime.now(pacific) - timedelta(days=3)
            ).date()
            st.session_state.end_time = (datetime.now(pacific)).date()
        case "Last 7 days":
            st.session_state.start_time = (
                datetime.now(pacific) - timedelta(days=7)
            ).date()
            st.session_state.end_time = (datetime.now(pacific)).date()
        case "Last week":
            today = datetime.now().weekday() + 1
            sunday = (datetime.now() - timedelta(days=today)).date()
            prev_sunday = sunday - timedelta(days=7)
            st.session_state.start_time = prev_sunday
            st.session_state.end_time = sunday


def plot_chart(df: pd.DataFrame):
    if len(df) == 0:
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
        series.append(
            {
                "name": str(col),
                "type": "bar",
                "stack": "total",
                "emphasis": {"focus": "series"},
                "data": resampled[col].tolist(),
                "itemStyle": {"borderRadius": [2, 2, 0, 0]},
            }
        )

    options = {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "item",
            "formatter": "<b>{a}</b><br/>{b}: <b>{c} units</b>",
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
        "color": colors,
    }
    with chart_area:
        st_echarts(options=options, height="550px")


### Layout ###
if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.now(pacific) - timedelta(days=3)
    st.session_state.end_time = datetime.now(pacific)

button_name = "Refresh" if "hourly_report" in st.session_state else "Pull data"

start_time_col, end_time_col, time_options_col, button_col, curr_time_col = st.columns(
    [3, 3, 4, 2, 2], vertical_alignment="bottom"
)
coll_select, size_select, color_select, sales_channel_select = st.columns([2, 1, 2, 2])
metric_area = st.container()
unit_metric, order_metric, dollar_metric, price_metric, aov_metric, cancelled_metric = (
    metric_area.columns([1, 1, 1, 1, 1, 1])
)
with st.expander("Raw data"):
    analysis_df_area = st.container()
    total_df_area = st.container()
    sku_df_area, order_df_area, promo_df_area = analysis_df_area.columns([1, 1, 1])
with curr_time_col:
    time_slot = st.empty()
update_pst_time(time_slot)

chart_area = st.container()
add_chart_area = st.container()

filtered_dict: pd.DataFrame = filter_dictionary(
    coll_target=coll_select, size_target=size_select, color_target=color_select
)
start_time = start_time_col.datetime_input(
    label="Start time (Pacific)", value=st.session_state.start_time, disabled=True
)
end_time = end_time_col.datetime_input(
    label="End time (Pacific)", value=st.session_state.end_time, disabled=True
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
if button_col.button(button_name, on_click=apply_options):
    if (end_time - start_time).days > 8:
        st.warning("Too long period, use Sales Trends dashboard instead")
    else:
        with st.spinner():
            st.session_state.hourly_report = asyncio.run(
                get_orders_data(
                    start_time=start_time.replace(tzinfo=pacific).astimezone(utc),
                    end_time=end_time.replace(tzinfo=pacific).astimezone(utc),
                )
            )

if "hourly_report" in st.session_state:
    if isinstance(st.session_state.hourly_report, pd.DataFrame):
        sales_channels = (
            st.session_state.hourly_report["sales-channel"].unique().tolist()
        )
        sales_channel = sales_channel_select.multiselect(
            label="Sales channel",
            options=sales_channels,
            default="Amazon.com" if "Amazon.com" in sales_channels else sales_channels,
        )
        report_filtered = st.session_state.hourly_report.copy()
        report_filtered = report_filtered.loc[
            (report_filtered["asin"].isin(filtered_dict["asin"].values.tolist()))
            & (report_filtered["sales-channel"].isin(sales_channel))
        ]

        plot_chart(report_filtered)

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

        unit_metric.metric(label="Units", value=total_units, format="localized")
        order_metric.metric(label="Orders", value=total_orders)
        dollar_metric.metric(label="Revenue", value=total_revenue, format="dollar")
        price_metric.metric(label="Average price", value=average_price, format="dollar")
        aov_metric.metric(label="AOV", value=aov, format="dollar")
        cancelled_metric.metric(
            label="Cancelled orders", value=cancelled_orders, format="localized"
        )

        total_df_area.caption("Raw order data")
        total_df_area.dataframe(report_filtered, hide_index=True)
        top_skus, top_orders, top_promos = analyze_orders(report_filtered)
        sku_df_area.caption("Top SKUs")
        sku_df_area.dataframe(
            top_skus,
            hide_index=True,
            column_config={"sku": st.column_config.LinkColumn(display_text=r"#(.*)")},
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
