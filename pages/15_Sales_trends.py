import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from login import require_login
from modules.events import event_dates_list

import os

os.makedirs("temp", exist_ok=True)
tempfile = os.path.join("temp", "sales.csv")

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
]
if not st.user.email in sales_users:
    st.toast(
        f"User {st.user.email} does not have access to sales data. Contact Sergey for details"
    )
    st.stop()

collection_area, size_area, color_area = st.columns([2, 1, 1])
events_checkbox, changes_checkbox, lds_checkbox = st.columns([1, 1, 1])

GC_CREDENTIALS = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)


@st.cache_data(ttl=3600)
def get_sales_data(interval: str = "2 YEAR") -> pd.DataFrame | None:
    query = f"""
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
            sessions_data AS (
            SELECT
                DATE(date) AS date,
                childAsin AS asin,
                SUM(sessions) AS sessions
            FROM mellanni-project-da.reports.business_report_asin
            WHERE DATE(date) >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
                AND LOWER(country_code) = 'us'
            GROUP BY date, asin
            ),
            inventory_by_date_asin AS (
            SELECT
                DATE(snapshot_date) AS date,
                asin,
                SUM(Inventory_Supply_at_FBA) AS inventory_supply_at_fba
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
                ANY_VALUE(short_title) AS short_title
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
            sd.sessions,
            inv.inventory_supply_at_fba,
            ca.change_notes
            FROM sales s
            LEFT JOIN sessions_data sd
            ON s.asin = sd.asin
            AND s.date = sd.date
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
    try:
        with bigquery.Client(
            credentials=GC_CREDENTIALS, project=GC_CREDENTIALS.project_id
        ) as client:
            result = client.query(query).to_dataframe()
        return result
    except Exception as e:
        st.error(f"Error while pulling BQ data: {e}")


def filtered_sales(sales: pd.DataFrame, sel_collection, sel_size, sel_color):
    if sel_collection:
        sales = sales[sales["collection"].isin(sel_collection)]
    if sel_size:
        sales = sales[sales["size"].isin(sel_size)]
    if sel_color:
        sales = sales[sales["color"].isin(sel_color)]
    combined = (
        sales.groupby("date")
        .agg(
            {
                "units": "sum",
                "net_sales": "sum",
                "sessions": "sum",
                "inventory_supply_at_fba": "sum",
                "change_notes": lambda x: ", ".join(
                    [note for note in x.unique() if note]
                ),
            }
        )
        .reset_index()
    )
    return combined


def create_plot(df, show_change_notes, show_lds):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["units"],
            name="units",
            yaxis="y1",
            line=dict(color="blue"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["30-day avg"],
            name="30-day avg",
            yaxis="y1",
            line=dict(dash="dash", color="lightblue"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["average selling price"],
            name="average selling price",
            yaxis="y2",
            line=dict(dash="dot", color="green"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sessions"],
            name="sessions",
            yaxis="y3",
            line=dict(dash="longdash", color="orange"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["inventory_supply_at_fba"],
            name="amz inventory supply",
            yaxis="y3",
            line=dict(dash="dot", color="pink"),
        )
    )

    if show_change_notes:
        for index, row in df.iterrows():
            condition = pd.notna(row["change_notes"]) and row["change_notes"] != ""
            if not show_lds:
                condition = (
                    pd.notna(row["change_notes"])
                    and row["change_notes"] != ""
                    and not (
                        row["change_notes"].startswith("LD")
                        or row["change_notes"].startswith("BD")
                    )
                )
            if condition:
                fig.add_annotation(
                    x=row["date"],
                    y=row["units"],
                    text="change",
                    hovertext=row["change_notes"],
                    showarrow=True,
                    arrowhead=1,
                    ax=0,
                    ay=-40,
                )

    fig.update_layout(
        title_text="Sales, ASP and Sessions Over Time",
        xaxis=dict(domain=[0.1, 0.9]),
        yaxis=dict(title="<b>Units</b> axis", side="left", rangemode="tozero"),
        yaxis2=dict(
            title="<b>Dollar</b>, $",
            side="right",
            overlaying="y",
            anchor="x",
            rangemode="tozero",
        ),
        yaxis3=dict(
            title="<b>Sessions</b>",
            side="right",
            overlaying="y",
            anchor="free",
            position=1,
            rangemode="tozero",
        ),
    )

    st.plotly_chart(fig)


if "sales" not in st.session_state and not os.path.exists(tempfile):
    st.session_state["sales"] = get_sales_data()
    if isinstance(st.session_state["sales"], pd.DataFrame):
        st.session_state["sales"].to_csv(tempfile, index=False)
elif os.path.exists(tempfile):
    st.session_state["sales"] = pd.read_csv(tempfile)

st.session_state["sales"]["date"] = pd.to_datetime(st.session_state["sales"]["date"])
st.session_state["sales"]["change_notes"] = st.session_state["sales"][
    "change_notes"
].fillna("")

if (pd.to_datetime("today") - pd.Timedelta(days=1)).date() not in st.session_state[
    "sales"
]["date"].dt.date.unique().tolist():
    st.session_state["sales"] = get_sales_data()
    if isinstance(st.session_state["sales"], pd.DataFrame):
        st.session_state["sales"].to_csv(tempfile, index=False)

sales = st.session_state["sales"].copy()

if sales is not None:
    collections = sales["collection"].unique()
    sizes = sales["size"].unique()
    colors = sales["color"].unique()

    include_events = events_checkbox.checkbox("Include events?", value=True)
    show_change_notes = changes_checkbox.checkbox("Show change notes?", value=True)
    show_lds = lds_checkbox.checkbox("Show LDs/BDs?", value=False)
    sel_collection = collection_area.multiselect("Collections", collections)
    sel_size = size_area.multiselect("Sizes", sizes)
    sel_color = color_area.multiselect("Colors", colors)

    combined = filtered_sales(sales, sel_collection, sel_size, sel_color)

    if not include_events:
        combined = combined[~combined["date"].isin(event_dates_list)]

    if not combined.empty:
        combined["30-day avg"] = combined["units"].rolling(window=30).mean().round(1)
        combined["average selling price"] = combined["net_sales"] / combined["units"]
        create_plot(combined, show_change_notes, show_lds)
    else:
        st.warning("No data to display for the selected filters.")
