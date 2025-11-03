import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from plotly.subplots import make_subplots
import plotly.graph_objects as go

from dateutil.relativedelta import relativedelta

from login import require_login
from modules.events import event_dates_list

import os

os.makedirs("temp", exist_ok=True)
sales_tempfile = os.path.join("temp", "sales.csv")
sessions_tempfile = os.path.join("temp", "sessions.csv")

st.set_page_config(
    page_title="Sales history", page_icon="media/logo.ico", layout="wide"
)

require_login()
sales_users = [
    "2djohar@gmail.com",
    "sergey@mellanni.com",
    "vitalii@mellanni.com",
    "ruslan@mellanni.com",
    "bohdan@mellanni.com",
    "igor@mellanni.com",
    "margarita@mellanni.com",
    "masao@mellanni.com",
    "valerii@mellanni.com",
]

GC_CREDENTIALS = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)

if st.user.email not in sales_users:
    st.toast(
        f"User {st.user.email} does not have access to sales data. Contact Sergey for details"
    )
    st.stop()

collection_area, size_area, color_area = st.columns([2, 1, 1])
(
    date_from_picker,
    date_to_picker,
    events_checkbox,
    changes_checkbox,
    lds_checkbox,
    inv_checkbox,
) = st.columns([2, 2, 1, 1, 1, 1])
date_range_area = st.empty()
metrics_area = st.container()
(
    units_metric,
    dollar_metric,
    price_metric,
    sessions_metric,
    conversion_metric,
    avg_units_metric,
    avg_dollar_metric,
    avg_sessions_metric,
) = metrics_area.columns([1, 1, 1, 1, 1, 1, 1, 1])
plot_area = st.container()
df_area_container = st.container()
df_text, df_top_sellers = df_area_container.columns([1, 10])


@st.cache_data(ttl=3600)
def get_sales_data(
    interval: str = "2 YEAR",
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    sales_query = f"""
            WITH sales AS (
            SELECT
                DATE(purchase_date, "America/Los_Angeles") AS date,
                asin,
                SUM(quantity) AS units,
                SUM(item_price) AS gross_item_sales,
                SUM(COALESCE(item_promotion_discount,0)) AS item_promo,
                SUM(COALESCE(item_price,0)) - SUM(COALESCE(item_promotion_discount,0)) AS net_sales
            FROM mellanni-project-da.reports.all_orders
            WHERE DATE(purchase_date, "America/Los_Angeles") >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
                AND LOWER(sales_channel) = 'amazon.com'
            GROUP BY date, asin
            ),
            total_sales AS (
            SELECT
                DATE(purchase_date, "America/Los_Angeles") AS date,
                SUM(quantity) AS total_units,
            FROM mellanni-project-da.reports.all_orders
            WHERE DATE(purchase_date, "America/Los_Angeles") >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
                AND LOWER(sales_channel) = 'amazon.com'
            GROUP BY date
            ),
            inventory_by_date_asin AS (
            SELECT
                DATE(snapshot_date) AS date,
                asin,
                SUM(Inventory_Supply_at_FBA) AS inventory_supply_at_fba,
                SUM(available) AS available
            FROM mellanni-project-da.reports.fba_inventory_planning
            WHERE DATE(snapshot_date) >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
                AND LOWER(marketplace) = 'us'
            GROUP BY date, asin
            ),
            deduped_dict AS (
            SELECT
                sku,
                asin,
                ANY_VALUE(collection)  AS collection,
                ANY_VALUE(size)        AS size,
                ANY_VALUE(color)       AS color,
            FROM mellanni-project-da.auxillary_development.dictionary
            WHERE sku IS NOT NULL OR asin IS NOT NULL
            GROUP BY sku, asin
            ),
            changelog_mapped AS (
            SELECT
                DATE(sc.date) AS date,
                sc.sku,
                sd.collection,
                sd.size,
                sd.color,
                sc.change_type,
                sc.notes
            FROM mellanni-project-da.auxillary_development.sku_changelog sc
            LEFT JOIN deduped_dict sd
                ON sc.sku = sd.sku
            WHERE DATE(sc.date) >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
            ),
            changelog_agg AS (
            SELECT
                date,
                collection,
                size,
                color,
                STRING_AGG(DISTINCT CONCAT(COALESCE(change_type,''), ': ', COALESCE(notes,'')), ' | ') AS change_notes
            FROM changelog_mapped
            WHERE collection IS NOT NULL AND size IS NOT NULL AND color IS NOT NULL
            GROUP BY date, collection, size, color
            ),
            deduped_asin_dict AS (
            SELECT
                asin,
                ANY_VALUE(collection)  AS collection,
                ANY_VALUE(size)        AS size,
                ANY_VALUE(color)       AS color
            FROM mellanni-project-da.auxillary_development.dictionary
            WHERE asin IS NOT NULL
            GROUP BY asin
            )
            SELECT
            s.date,
            s.asin,
            d.collection,
            d.size,
            d.color,
            s.units,
            s.net_sales,
            ts.total_units,
            inv.inventory_supply_at_fba,
            inv.available,
            ca.change_notes
            FROM sales s
            LEFT JOIN total_sales ts
            ON s.date = ts.date
            LEFT JOIN inventory_by_date_asin inv
            ON s.asin = inv.asin
            AND s.date = inv.date
            LEFT JOIN deduped_asin_dict d
            ON s.asin = d.asin
            LEFT JOIN changelog_agg ca
            ON s.date = ca.date
            AND d.collection = ca.collection
            AND d.size = ca.size
            AND d.color = ca.color
            ORDER BY s.date ASC, s.units DESC
            """

    sessions_query = f"""
            WITH sessions as (
            SELECT
                DATE(date) AS date,
                childAsin AS asin,
                SUM(sessions) AS sessions
            FROM mellanni-project-da.reports.business_report_asin
            WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL {interval})
                AND LOWER(country_code) = 'us'
            GROUP BY date, asin
            ),
            deduped_dict AS (
            SELECT
                asin,
                ANY_VALUE(collection)  AS collection,
                ANY_VALUE(size)        AS size,
                ANY_VALUE(color)       AS color,
            FROM mellanni-project-da.auxillary_development.dictionary
            WHERE asin IS NOT NULL
            GROUP BY asin
            )
            SELECT
            s.date,
            s.asin,
            s.sessions,
            d.collection,
            d.size,
            d.color,
            FROM sessions s
            LEFT JOIN deduped_dict d
            ON s.asin = d.asin
            ORDER BY s.date ASC, s.sessions DESC

            """

    try:
        with bigquery.Client(
            credentials=GC_CREDENTIALS, project=GC_CREDENTIALS.project_id
        ) as client:
            sales_job = client.query(sales_query)
            session_job = client.query(sessions_query)

            sales_df = sales_job.result().to_dataframe()
            sessions_df = session_job.result().to_dataframe()
        return sales_df, sessions_df
    except Exception as e:
        st.error(f"Error while pulling BQ data: {e}")
        return (None, None)


def filtered_sales(
    df: pd.DataFrame,
    sessions: pd.DataFrame,
    sel_collection,
    sel_size,
    sel_color,
    available_inv,
    date_range,
    periods,
):

    inv_column = "available" if available_inv else "inventory_supply_at_fba"

    if sel_collection:
        df = df[df["collection"].isin(sel_collection)]
        sessions = sessions[sessions["collection"].isin(sel_collection)]
    if sel_size:
        df = df[df["size"].isin(sel_size)]
        sessions = sessions[sessions["size"].isin(sel_size)]
    if sel_color:
        df = df[df["color"].isin(sel_color)]
        sessions = sessions[sessions["color"].isin(sel_color)]

    if not include_events:
        df = df[~df["date"].isin(event_dates_list)]
        sessions = sessions[~sessions["date"].isin(event_dates_list)]

    asin_sessions = sessions.groupby("asin").agg({"sessions": "sum"}).reset_index()
    date_sessions = sessions.groupby("date").agg({"sessions": "sum"}).reset_index()

    df["asin_30d_avg"] = df.groupby("asin")["units"].transform(
        lambda x: x.rolling(30, min_periods=1).mean()
    )
    df["asin_sales_share"] = df["asin_30d_avg"] / df.groupby("date")[
        "asin_30d_avg"
    ].transform("sum")
    df["stockout"] = (1 - (df[inv_column] / df["asin_30d_avg"]).clip(upper=1)) * df[
        "asin_sales_share"
    ]

    df["change_notes"] = df["change_notes"].fillna("")
    df = df.sort_values("date", ascending=True)

    asin_sales = df.copy()
    asin_sales["date"] = pd.to_datetime(asin_sales["date"]).dt.date
    asin_sales = asin_sales[asin_sales["date"].between(date_range[0], date_range[1])]

    asin_sales = (
        asin_sales.groupby("asin")
        .agg(
            {
                "collection": "first",
                "size": "first",
                "color": "first",
                "units": "sum",
                "net_sales": "sum",
                "available": "last",
                "inventory_supply_at_fba": "last",
            }
        )
        .reset_index()
        .sort_values("net_sales", ascending=False)
    )
    asin_sales = pd.merge(
        asin_sales, asin_sessions, how="left", on="asin", validate="1:1"
    ).fillna(0)

    asin_sales["sales_share"] = asin_sales["net_sales"] / asin_sales["net_sales"].sum()

    date_sessions["date"] = pd.to_datetime(date_sessions["date"]).dt.date
    combined = (
        df.groupby("date")
        .agg(
            {
                "units": "sum",
                "net_sales": "sum",
                "available": "sum",
                "inventory_supply_at_fba": "sum",
                "stockout": "sum",
                "change_notes": lambda x: ", ".join(
                    [note for note in x.unique() if note]
                ),
            }
        )
        .reset_index()
    )
    combined["date"] = pd.to_datetime(combined["date"]).dt.date
    combined = pd.merge(
        combined, date_sessions, how="left", on="date", validate="1:1"
    ).fillna(0)

    combined["30-day avg"] = combined["units"].rolling(window=30).mean().round(1)
    combined["average selling price"] = combined["net_sales"] / combined["units"]

    combined_visible = combined.copy()
    combined_visible["date"] = pd.to_datetime(combined_visible["date"]).dt.date

    match periods:
        case "custom":
            prev_start, prev_end = min_period, max_period

        case _:
            prev_start = date_range[0] - relativedelta(years=1)
            prev_end = date_range[1] - relativedelta(years=1)

    combined_previous = combined_visible[
        combined_visible["date"].between(prev_start, prev_end)
    ]
    combined_visible = combined_visible[
        combined_visible["date"].between(date_range[0], date_range[1])
    ]

    # Create a full date range from the selected date_range
    full_date_range = pd.date_range(start=date_range[0], end=date_range[1], freq="D")

    combined_visible[
        [
            "units",
            "net_sales",
            "available",
            "inventory_supply_at_fba",
            "stockout",
            "sessions",
            "30-day avg",
            "average selling price",
        ]
    ] = combined_visible[
        [
            "units",
            "net_sales",
            "available",
            "inventory_supply_at_fba",
            "stockout",
            "sessions",
            "30-day avg",
            "average selling price",
        ]
    ].astype(
        float
    )
    # Set 'date' as the index, reindex to the full date range, and then reset index
    combined_visible = (
        combined_visible.set_index("date")
        .reindex(full_date_range.date)
        .reset_index()
        .rename(columns={"index": "date"})
    )

    return combined_visible, combined_previous, asin_sales


def _top_n_sellers(asin_sales: pd.DataFrame, num_top_sellers: int) -> pd.DataFrame:
    asin_sales = asin_sales.head(num_top_sellers)
    totals_asins = asin_sales.sum(numeric_only=True, axis=0)
    asin_sales = pd.concat([asin_sales, pd.DataFrame(totals_asins).T])
    return asin_sales


def create_plot(df, show_change_notes, show_lds, available=True):
    # Defensive copy and basic normalization
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    else:
        df = df.reset_index().rename(columns={"index": "date"})
        df["date"] = pd.to_datetime(df["date"])
    inv_column = "available" if available else "inventory_supply_at_fba"
    # Prepare stockout values as fraction (0.15) and negate for plotting below zero
    stockout_raw = pd.to_numeric(df.get("stockout", 0)).fillna(0)
    stockout_frac = stockout_raw / 100.0 if stockout_raw.max() > 1 else stockout_raw
    stockout_y = -stockout_frac
    # Create two-row figure: top = main metrics, bottom = stockout (negative axis, isolated)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.05,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
    )
    # Top row traces (primary left y for units, 30-day avg; secondary right y for price)
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["units"], name="units", line=dict(color="blue")),
        row=1,
        col=1,
        secondary_y=False,
    )
    if "30-day avg" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["30-day avg"],
                name="30-day avg",
                line=dict(dash="dash", color="lightblue"),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
    # Price — attach to the built-in secondary y (yaxis2)
    if "average selling price" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["average selling price"],
                name="avg price",
                line=dict(dash="dot", color="green"),
                hovertemplate="%{y:$,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=True,
        )
        # ensure last-added trace is mapped to yaxis2
        fig.data[-1].update(yaxis="y2")
    # Sessions — put on its own left-side axis (yaxis4) mapped to left but free-positioned
    if "sessions" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["sessions"],
                name="sessions",
                line=dict(dash="dot", color="orange"),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.data[-1].update(yaxis="y4")
    # Inventory — its own overlaying right axis (yaxis5)
    if inv_column in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[inv_column],
                name="amz inventory available" if available else "amz inventory total",
                line=dict(dash="dot", color="pink"),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.data[-1].update(yaxis="y5")
    # Bottom row: stockout as negative filled area to zero (isolated axis with negative ticks)
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=stockout_y,
            name="stockout",
            fill="tozeroy",
            fillcolor="rgba(255,0,0,0.25)",
            line=dict(width=0),
            hovertemplate="%{y:.1%}<extra></extra>",
            showlegend=True,
        ),
        row=2,
        col=1,
    )
    # Optional annotations (kept in top row, anchored to units)
    if show_change_notes and "change_notes" in df.columns:
        for _, row in df.iterrows():
            txt = row.get("change_notes")
            if not pd.isna(txt) and txt != "":
                if not show_lds and (
                    str(txt).startswith("LD") or str(txt).startswith("BD")
                ):
                    continue
                fig.add_annotation(
                    x=row["date"],
                    y=row.get("units", 0),
                    text="change",
                    hovertext=str(txt),
                    showarrow=True,
                    arrowhead=1,
                    ax=0,
                    ay=-40,
                    row=1,
                    col=1,
                )
    # Axis & layout configuration
    y1_title = "<b>Units sold</b>"
    y2_title = "<b>Average selling price</b>"
    y4_title = "<b>Sessions</b>"
    y5_title = "<b>AMZ inventory supply</b>"
    y3_title = "<b>Stockout</b>"
    # Compute safe ranges for axes to avoid squashing:
    if "average selling price" in df.columns:
        price_min = float(df["average selling price"].min())
        price_max = float(df["average selling price"].max())
        if price_min == price_max:
            price_min -= max(1.0, abs(price_min) * 0.05)
            price_max += max(1.0, abs(price_max) * 0.05)
        price_range = [price_min * 0.98, price_max * 1.02]
    else:
        price_range = None
    if "sessions" in df.columns:
        sess_min = float(df["sessions"].min())
        sess_max = float(df["sessions"].max())
        if sess_min == sess_max:
            sess_min = 0
            sess_max = sess_max + max(1.0, abs(sess_max) * 0.05)
        sess_range = [sess_min * 0.98, sess_max * 1.02]
    else:
        sess_range = None
    if inv_column in df.columns:
        inv_min = float(df[inv_column].min())
        inv_max = float(df[inv_column].max())
        if inv_min == inv_max:
            inv_min = 0
            inv_max = inv_max + max(1.0, abs(inv_max) * 0.05)
        inv_range = [inv_min * 0.98, inv_max * 1.02]
    else:
        inv_range = None
    # Determine sensible stockout range
    min_stockout = float(stockout_y.min()) if len(stockout_y) > 0 else 0.0
    y3_min = min_stockout * 1.1 if min_stockout < 0 else -0.1
    # Position main left axis inward so the sessions left axis has room outside it
    layout_yaxis_main = dict(title=y1_title, position=0.12, zeroline=True)
    # Sessions axis on left but positioned left of the main axis (anchor free)
    layout_yaxis4 = dict(
        title=y4_title,
        overlaying="y",
        side="left",
        anchor="free",
        position=0.02,  # slightly left of the main left axis
        showgrid=False,
        zeroline=False,
        tickfont=dict(color="orange"),
    )
    if sess_range:
        layout_yaxis4["range"] = sess_range  # type: ignore
    # Price axis on right (yaxis2)
    layout_yaxis2 = dict(
        title=y2_title,
        overlaying="y",
        side="right",
        anchor="x",
        position=0.88,
        showgrid=False,
        zeroline=False,
    )
    if price_range:
        layout_yaxis2["range"] = price_range  # type: ignore
    # Inventory axis on far right (yaxis5)
    layout_yaxis5 = dict(
        title=y5_title,
        overlaying="y",
        side="right",
        anchor="x",
        position=0.985,
        showgrid=False,
        zeroline=False,
    )
    if inv_range:
        layout_yaxis5["range"] = inv_range  # type: ignore
    fig.update_layout(
        title_text="Sales, ASP and Sessions Over Time",
        legend=dict(orientation="v", x=1.02, y=1),
        margin=dict(
            l=180, r=180, t=80, b=60
        ),  # increased left margin to avoid label clipping
        hovermode="x unified",
        yaxis=layout_yaxis_main,
        yaxis2=layout_yaxis2,
        yaxis4=layout_yaxis4,
        yaxis5=layout_yaxis5,
    )
    fig.update_yaxes(title_text=y1_title, row=1, col=1, zeroline=True)
    fig.update_yaxes(
        title_text=y3_title,
        row=2,
        col=1,
        zeroline=True,
        showgrid=False,
        tickformat=".0%",
        range=[y3_min, 0],
    )
    # Tweak x-axis appearance (shared)
    fig.update_xaxes(showspikes=True, spikecolor="grey", spikesnap="cursor")
    # Render
    plot_area.plotly_chart(fig, use_container_width=True)


if "sales" not in st.session_state or "sessions" not in st.session_state:
    if os.path.exists(sales_tempfile) and os.path.exists(sessions_tempfile):
        st.session_state["sales"] = pd.read_csv(sales_tempfile, parse_dates=["date"])
        st.session_state["sales"]["date"] = pd.to_datetime(
            st.session_state["sales"]["date"]
        ).dt.date
        st.session_state["sessions"] = pd.read_csv(
            sessions_tempfile, parse_dates=["date"]
        )
        st.session_state["sessions"]["date"] = pd.to_datetime(
            st.session_state["sessions"]["date"]
        ).dt.date
    else:
        st.session_state["sales"], st.session_state["sessions"] = get_sales_data()
        if isinstance(st.session_state["sales"], pd.DataFrame):
            st.session_state["sales"].to_csv(sales_tempfile, index=False)
        if isinstance(st.session_state["sessions"], pd.DataFrame):
            st.session_state["sessions"].to_csv(sessions_tempfile, index=False)


# if (
#     st.session_state["sales"]["date"].max()
#     < (pd.to_datetime("today") - pd.Timedelta(days=1)).date()
# ):
#     st.session_state["sales"], st.session_state["sessions"] = get_sales_data()
#     if isinstance(st.session_state["sales"], pd.DataFrame):
#         st.session_state["sales"].to_csv(sales_tempfile, index=False)
#     if isinstance(st.session_state["sessions"], pd.DataFrame):
#         st.session_state["sessions"].to_csv(sessions_tempfile, index=False)

sales = st.session_state["sales"].copy()
sessions = st.session_state["sessions"].copy()

if sales is not None:
    collections = sales["collection"].unique()
    sizes = sales["size"].unique()
    colors = sales["color"].unique()
    min_date = sales["date"].min()
    max_date = sales["date"].max()
    date_range = (
        date_from_picker.date_input(
            "Start date",
            value=max_date - pd.Timedelta(days=90),
            min_value=min_date,
            max_value=max_date,
            width=150,
        ),
        date_to_picker.date_input(
            "End date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            width=150,
        ),
    )

    with st.sidebar:
        periods = st.radio("Compare periods", options=["last year", "custom"])
        min_period, max_period = max_date - relativedelta(
            years=1, days=90
        ), max_date - relativedelta(years=1)
        if periods == "custom":
            min_period = st.date_input(
                "Date from", value=max_date - relativedelta(years=1, days=90)
            )
            max_period = st.date_input(
                "Date to", value=max_date - relativedelta(years=1)
            )

    include_events = events_checkbox.checkbox("Include events?", value=True)
    show_change_notes = changes_checkbox.checkbox("Show change notes?", value=True)
    show_lds = lds_checkbox.checkbox("Show LDs/BDs?", value=False)
    available_inv = inv_checkbox.checkbox("Show only available inventory", value=True)
    sel_collection = collection_area.multiselect("Collections", collections)
    sel_size = size_area.multiselect("Sizes", sizes)
    sel_color = color_area.multiselect("Colors", colors)

    combined, combined_previous, asin_sales = filtered_sales(
        sales.copy(),
        sessions,
        sel_collection,
        sel_size,
        sel_color,
        available_inv,
        date_range,
        periods,
    )

    if not combined.empty:
        create_plot(combined, show_change_notes, show_lds, available_inv)
        # absolute numbers metrics
        total_units_this_year = combined["units"].sum()
        total_units_last_year = combined_previous["units"].sum()
        total_dollars_this_year = combined["net_sales"].sum()
        total_dollars_last_year = combined_previous["net_sales"].sum()
        average_price_this_year = total_dollars_this_year / total_units_this_year
        average_price_last_year = total_dollars_last_year / total_units_last_year
        sessions_this_year = combined["sessions"].sum()
        sessions_last_year = combined_previous["sessions"].sum()
        conversion_this_year = total_units_this_year / sessions_this_year
        conversion_last_year = total_units_last_year / sessions_last_year

        # average numbers metrics
        days_this_year = (date_range[1] - date_range[0]).days + 1
        days_last_year = (max_period - min_period).days + 1
        average_units_this_year = combined["units"].sum() / days_this_year
        average_units_last_year = combined_previous["units"].sum() / days_last_year
        average_dollars_this_year = combined["net_sales"].sum() / days_this_year
        average_dollars_last_year = combined_previous["net_sales"].sum() / days_last_year
        average_sessions_this_year = combined["sessions"].sum() / days_this_year
        average_sessions_last_year = combined_previous["sessions"].sum() / days_last_year

        metric_text = (
            f"{min_period} - {max_period}"
            if periods == "custom"
            else "Same period last year"
        )
        yoy_text = "YoY" if periods == "last year" else "vs Period"

        units_metric.metric(
            label="Total units sold",
            value=f"{total_units_this_year:,.0f}",
            delta=f"{total_units_this_year / total_units_last_year -1:.1%} {yoy_text}",
            chart_data=combined["units"],
            help=f"{metric_text}: {total_units_last_year:,.0f}",
        )
        dollar_metric.metric(
            label="Total sales",
            value=f"${total_dollars_this_year:,.0f}",
            delta=f"{total_dollars_this_year / total_dollars_last_year -1:.1%} {yoy_text}",
            chart_data=combined["net_sales"],
            help=f"{metric_text}: ${total_dollars_last_year:,.0f}",
        )
        price_metric.metric(
            label="Average price",
            value=f"${average_price_this_year:,.2f}",
            delta=f"{average_price_this_year / average_price_last_year - 1:.1%} {yoy_text}",
            chart_data=combined["net_sales"] / combined["units"],
            help=f"{metric_text}: ${average_price_last_year:,.2f}",
        )
        sessions_metric.metric(
            label="Total sessions",
            value=f"{sessions_this_year:,.0f}",
            delta=f"{sessions_this_year / sessions_last_year - 1:.1%} {yoy_text}",
            chart_data=combined["sessions"],
            help=f"{metric_text}: {sessions_last_year:,.0f}",
        )
        conversion_metric.metric(
            label="Conversion %",
            value=f"{conversion_this_year:.1%}",
            delta=f"{conversion_this_year / conversion_last_year - 1:.1%} {yoy_text}",
            chart_data=(combined["units"] / combined["sessions"] * 100).round(1),
            help=f"{metric_text}: {conversion_last_year:.1%}",
        )

        avg_units_metric.metric(
            label="Avg units/day",
            value=f"{average_units_this_year:,.1f}" if average_units_this_year > 1 else f"{average_units_this_year:.3f}",
            delta=f"{average_units_this_year / average_units_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: {average_units_last_year:,.1f}" if average_units_last_year > 1 else f"{metric_text}: {average_units_last_year:,.3f}",
        )
        avg_dollar_metric.metric(
            label="Avg sales/day",
            value=f"${average_dollars_this_year:,.0f}",
            delta=f"{average_dollars_this_year / average_dollars_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: ${average_dollars_last_year:,.0f}",
        )
        avg_sessions_metric.metric(
            label="Avg sessions/day",
            value=f"{average_sessions_this_year:,.0f}",
            delta=f"{average_sessions_this_year / average_sessions_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: {average_sessions_last_year:,.0f}",
        )

        num_top_sellers = df_top_sellers.number_input(
            "Select top n sellers", min_value=2, max_value=10000, value=10, width=150
        )
        df_text.text(f"Top {num_top_sellers} sellers")
        asin_sales_top = _top_n_sellers(asin_sales, num_top_sellers)
        asin_sales_top["asin"] = "https://www.amazon.com/dp/" + asin_sales_top["asin"]
        df_area_container.data_editor(
            asin_sales_top,
            num_rows="fixed",
            hide_index=True,
            column_order=[
                "asin",
                "collection",
                "size",
                "color",
                "units",
                "net_sales",
                "sales_share",
                "sessions",
                "available",
                "inventory_supply_at_fba",
            ],
            column_config={
                "asin": st.column_config.LinkColumn(
                    display_text="https://www\\.amazon\\.com/dp/(.*)"
                ),
                "units": st.column_config.NumberColumn(format="localized"),
                "net_sales": st.column_config.NumberColumn(format="dollar"),
                "sales_share": st.column_config.NumberColumn(format="percent"),
                "sessions": st.column_config.NumberColumn(format="localized"),
                "available": st.column_config.NumberColumn(format="localized"),
                "inventory_supply_at_fba": st.column_config.NumberColumn(
                    format="localized"
                ),
            },
        )
    else:
        st.warning("No data to display for the selected filters.")


# column_config={
# >>>         "command": "Streamlit Command",
# >>>         "rating": st.column_config.NumberColumn(
# >>>             "Your rating",
# >>>             help="How much do you like this command (1-5)?",
# >>>             min_value=1,
# >>>             max_value=5,
# >>>             step=1,
# >>>             format="%d ⭐",
# >>>         ),
# >>>         "is_widget": "Widget ?",
# >>>     },
