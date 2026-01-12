import streamlit as st
from numpy import nan
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account


from dateutil.relativedelta import relativedelta

from login import require_login
from common.events import event_dates_list
from modules.sales_charts import render_sales_chart

import os

os.makedirs("temp", exist_ok=True)
sales_tempfile = os.path.join("temp", "sales.parquet")
sessions_tempfile = os.path.join("temp", "sessions.parquet")
ads_tempfile = os.path.join("temp", "ads.parquet")
forecast_tempfile = os.path.join("temp", "forecast.parquet")

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
ad_metrics_area1 = st.container()
ad_metrics_area2 = st.container()
(
    ad_units_metric,
    ad_sales_metric,
    ad_spend_metric,
    ad_impressions_metric,
    ad_clicks_metric,
    ad_conversion_metric,
    ad_cpc_metric,
    ad_acos_metric,
) = ad_metrics_area1.columns([1, 1, 1, 1, 1, 1, 1, 1])
df_area_container = st.container()
df_text, df_top_sellers = df_area_container.columns([1, 10])


# @st.cache_data(
#     ttl=3600,
#     show_spinner="Please wait, pulling sales data from BigQuery...",
#     max_entries=3,
# )
def get_sales_data(
    interval: str = "3 YEAR",
) -> tuple[
    pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None
]:
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

    ads_query = f"""
            WITH advertised AS (
            SELECT
                DATE(date) AS date,
                advertisedAsin AS asin,
                SUM(spend) AS ad_spend,  -- Switched to 'spend' (total ad cost per schema); revert to 'cost' if intended
                SUM(impressions) AS impressions,
                SUM(clicks) AS clicks,
                SUM(unitsSoldSameSku14d) AS same_units,
                SUM(attributedSalesSameSku14d) AS same_sales
            FROM mellanni-project-da.reports.AdvertisedProduct
            WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL {interval})
                AND LOWER(country_code) = 'us'
            GROUP BY date, asin
            ),
            purchased AS (
            SELECT
                DATE(date) AS date,
                purchasedAsin AS asin,
                SUM(unitsSoldOtherSku14d) AS other_units,
                SUM(salesOtherSku14d) AS other_sales
            FROM mellanni-project-da.reports.PurchasedProduct
            WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL {interval})
                AND LOWER(country_code) = 'us'
            GROUP BY date, asin
            ),
            deduped_dict AS (
            SELECT
                asin,
                ANY_VALUE(collection) AS collection,
                ANY_VALUE(size) AS size,
                ANY_VALUE(color) AS color
            FROM mellanni-project-da.auxillary_development.dictionary
            WHERE asin IS NOT NULL
            GROUP BY asin
            )
            SELECT
            COALESCE(a.date, p.date) AS date,
            COALESCE(a.asin, p.asin) AS asin,
            a.ad_spend,
            a.impressions,
            a.clicks,
            COALESCE(a.same_units, 0) + COALESCE(p.other_units, 0) AS total_units,
            COALESCE(a.same_sales, 0) + COALESCE(p.other_sales, 0) AS total_sales,
            d.collection,
            d.size,
            d.color
            FROM advertised a
            FULL OUTER JOIN purchased p
            ON a.date = p.date AND a.asin = p.asin
            LEFT JOIN deduped_dict d
            ON COALESCE(a.asin, p.asin) = d.asin
            ORDER BY date ASC, asin;    
    """

    forecast_query = "SELECT date, asin, units as forecast_units FROM mellanni-project-da.daily_reports.forecast ORDER BY date, asin"
    try:
        with bigquery.Client(
            credentials=GC_CREDENTIALS, project=GC_CREDENTIALS.project_id
        ) as client:
            sales_job = client.query(sales_query)
            session_job = client.query(sessions_query)
            ads_job = client.query(ads_query)
            forecast_job = client.query(forecast_query)

            sales_df = sales_job.to_dataframe()
            sessions_df = session_job.to_dataframe()
            ads_df = ads_job.to_dataframe()
            forecast_df = forecast_job.to_dataframe()

            # sales_df[["collection", "size", "color"]] = sales_df[
            #     ["collection", "size", "color"]
            # ].astype("category")
            # sessions_df[["collection", "size", "color"]] = sales_df[
            #     ["collection", "size", "color"]
            # ].astype("category")
            # ads_df[["collection", "size", "color"]] = sales_df[
            #     ["collection", "size", "color"]
            # ].astype("category")

        return sales_df, sessions_df, ads_df, forecast_df
    except Exception as e:
        st.error(f"Error while pulling BQ data: {e}")
        return (None, None, None, None)


# @st.cache_data(ttl=3600, show_spinner="Filtering data...")
def filtered_sales(
    sales_df: pd.DataFrame,
    sessions_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    sel_collection,
    sel_size,
    sel_color,
    available_inv,
    include_events,
    date_range,
    periods,
):
    match periods:
        case "custom":
            prev_start, prev_end = min_period, max_period

        case "last week":
            prev_start = date_range[0] - relativedelta(weeks=1)
            prev_end = date_range[1] - relativedelta(weeks=1)

        case _:
            prev_start = date_range[0] - relativedelta(years=1)
            prev_end = date_range[1] - relativedelta(years=1)

    inv_column = "available" if available_inv else "inventory_supply_at_fba"

    sales_df = sales_df[
        sales_df["date"].between(prev_start - relativedelta(days=60), date_range[1])
    ]
    sessions_df = sessions_df[
        sessions_df["date"].between(prev_start - relativedelta(days=60), date_range[1])
    ]
    ads_df = ads_df[
        ads_df["date"].between(prev_start - relativedelta(days=60), date_range[1])
    ]

    forecast_df["date"] = pd.to_datetime(forecast_df["date"]).dt.date
    forecast_df = forecast_df[
        forecast_df["date"].between(prev_start - relativedelta(days=60), date_range[1])
    ]

    if sel_collection:
        sales_df = sales_df[sales_df["collection"].isin(sel_collection)]
        sessions_df = sessions_df[sessions_df["collection"].isin(sel_collection)]
        ads_df = ads_df[ads_df["collection"].isin(sel_collection)]
    if sel_size:
        sales_df = sales_df[sales_df["size"].isin(sel_size)]
        sessions_df = sessions_df[sessions_df["size"].isin(sel_size)]
        ads_df = ads_df[ads_df["size"].isin(sel_size)]
    if sel_color:
        sales_df = sales_df[sales_df["color"].isin(sel_color)]
        sessions_df = sessions_df[sessions_df["color"].isin(sel_color)]
        ads_df = ads_df[ads_df["color"].isin(sel_color)]

    # merge sales_df with forecast_df
    sales_asins = sales_df["asin"].unique()
    forecast_asins = forecast_df[forecast_df["asin"].isin(sales_asins)].copy()
    sales_df = pd.merge(
        sales_df, forecast_asins, how="outer", on=["date", "asin"], validate="1:1"
    )

    if not include_events:
        sales_df = sales_df[~sales_df["date"].isin(event_dates_list)]
        sessions_df = sessions_df[~sessions_df["date"].isin(event_dates_list)]
        ads_df = ads_df[~ads_df["date"].isin(event_dates_list)]

    asin_sessions = sessions_df.groupby("asin").agg({"sessions": "sum"}).reset_index()
    date_sessions = sessions_df.groupby("date").agg({"sessions": "sum"}).reset_index()

    # asin_ads = ads_df.groupby("asin")[['ad_spend', 'impressions', 'clicks', 'total_units',
    #    'total_sales']].agg('sum').reset_index()
    date_ads = (
        ads_df.groupby("date")[
            ["ad_spend", "impressions", "clicks", "total_units", "total_sales"]
        ]
        .agg("sum")
        .reset_index()
    )

    ads_previous = date_ads[date_ads["date"].between(prev_start, prev_end)]
    ads_visible = date_ads[date_ads["date"].between(date_range[0], date_range[1])]

    sales_df["asin_30d_avg"] = sales_df.groupby("asin")["units"].transform(
        lambda x: x.rolling(30, min_periods=1).mean()
    )
    sales_df["asin_sales_share"] = sales_df["asin_30d_avg"] / sales_df.groupby("date")[
        "asin_30d_avg"
    ].transform("sum")
    sales_df["stockout"] = (
        1 - (sales_df[inv_column] / sales_df["asin_30d_avg"]).clip(upper=1)
    ) * sales_df["asin_sales_share"]

    sales_df["change_notes"] = sales_df["change_notes"].fillna("")
    sales_df = sales_df.sort_values("date", ascending=True)

    asin_sales = sales_df.copy()
    # asin_sales["date"] = pd.to_datetime(asin_sales["date"]).dt.date
    asin_sales = asin_sales[asin_sales["date"].between(date_range[0], date_range[1])]

    asin_sales = (
        asin_sales.groupby("asin")
        .agg(
            {
                "collection": "first",
                "size": "first",
                "color": "first",
                "units": "sum",
                "forecast_units": "sum",
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
    )
    # asin_sales['sessions'] = asin_sales['sessions'].fillna(0)

    asin_sales["sales_share"] = asin_sales["net_sales"] / asin_sales["net_sales"].sum()

    date_sessions["date"] = pd.to_datetime(date_sessions["date"]).dt.date
    combined = (
        sales_df.groupby("date")
        .agg(
            {
                "units": "sum",
                "forecast_units": "sum",
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
    combined["30-day sales avg"] = (
        combined["net_sales"].rolling(window=30).mean().round(1)
    )
    combined["30-day sessions avg"] = (
        combined["sessions"].rolling(window=30).mean().round(1)
    )
    combined["average selling price"] = combined["net_sales"] / combined["units"]

    combined_visible = combined.copy()
    combined_visible["date"] = pd.to_datetime(combined_visible["date"]).dt.date

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
            "forecast_units",
            "net_sales",
            "available",
            "inventory_supply_at_fba",
            "stockout",
            "sessions",
            "30-day avg",
            "30-day sales avg",
            "30-day sessions avg",
            "average selling price",
        ]
    ] = combined_visible[
        [
            "units",
            "forecast_units",
            "net_sales",
            "available",
            "inventory_supply_at_fba",
            "stockout",
            "sessions",
            "30-day avg",
            "30-day sales avg",
            "30-day sessions avg",
            "average selling price",
        ]
    ].astype(
        float
    )

    # Apply event filtering as NULLs (gaps) instead of removing rows
    # Logic reverted: filtered_sales now removes rows for correct metrics.
    # Gaps are created by reindexing below.
    # if not include_events:
    #     mask = combined_visible["date"].isin(event_dates_list)
    #     cols_to_null = ["units", "sessions", "net_sales", "stockout", "available", "inventory_supply_at_fba"]
    #     combined_visible.loc[mask, cols_to_null] = None

    #     # Also apply to ads_visible
    #     mask_ads = ads_visible["date"].isin(event_dates_list)
    #     cols_to_null_ads = ["ad_spend", "total_sales", "impressions", "clicks"]
    #     # Ensure columns exist before assigning
    #     cols_existing = [c for c in cols_to_null_ads if c in ads_visible.columns]
    #     if cols_existing:
    #         ads_visible.loc[mask_ads, cols_existing] = None
    # Set 'date' as the index, reindex to the full date range, and then reset index
    combined_visible = (
        combined_visible.set_index("date")
        .reindex(full_date_range.date)
        .reset_index()
        .rename(columns={"index": "date"})
    )

    ads_visible = (
        ads_visible.set_index("date")
        .reindex(full_date_range.date)
        .reset_index()
        .rename(columns={"index": "date"})
        # .fillna(0)
    )

    return combined_visible, combined_previous, asin_sales, ads_visible, ads_previous


def _top_n_sellers(asin_sales: pd.DataFrame, num_top_sellers: int) -> pd.DataFrame:
    asin_sales = asin_sales.head(num_top_sellers)
    totals_asins = asin_sales.sum(numeric_only=True, axis=0)
    asin_sales = pd.concat([asin_sales, pd.DataFrame(totals_asins).T])
    return asin_sales


if (
    "sales" not in st.session_state
    or "sessions" not in st.session_state
    or "ads" not in st.session_state
    or "forecast" not in st.session_state
):
    if (
        os.path.exists(sales_tempfile)
        and os.path.exists(sessions_tempfile)
        and os.path.exists(ads_tempfile)
        and os.path.exists(forecast_tempfile)
    ):
        st.session_state["sales"] = pd.read_parquet(sales_tempfile)
        st.session_state["sessions"] = pd.read_parquet(sessions_tempfile)
        st.session_state["ads"] = pd.read_parquet(ads_tempfile)
        st.session_state["forecast"] = pd.read_parquet(forecast_tempfile)
    else:
        (
            st.session_state["sales"],
            st.session_state["sessions"],
            st.session_state["ads"],
            st.session_state["forecast"],
        ) = get_sales_data()
        if isinstance(st.session_state["sales"], pd.DataFrame):
            st.session_state["sales"].to_parquet(sales_tempfile, index=False)
        if isinstance(st.session_state["sessions"], pd.DataFrame):
            st.session_state["sessions"].to_parquet(sessions_tempfile, index=False)
        if isinstance(st.session_state["ads"], pd.DataFrame):
            st.session_state["ads"].to_parquet(ads_tempfile, index=False)
        if isinstance(st.session_state["forecast"], pd.DataFrame):
            st.session_state["forecast"].to_parquet(forecast_tempfile, index=False)


sales = st.session_state["sales"].copy()
# sales['date'] = pd.to_datetime(sales['date']).dt.date
sessions = st.session_state["sessions"].copy()
# sessions['date'] = pd.to_datetime(sessions['date']).dt.date
ads = st.session_state["ads"].copy()
# ads['date'] = pd.to_datetime(ads['date']).dt.date
forecast = st.session_state["forecast"].copy()

if (
    sales is not None
    and sessions is not None
    and ads is not None
    and forecast is not None
):
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
        options = ["last year", "custom"]
        if (date_range[1] - date_range[0]).days == 6:
            options = ["last week", "last year", "custom"]
        periods = st.radio("Compare periods", options=options)
        min_period, max_period = date_range[0] - relativedelta(years=1), date_range[
            1
        ] - relativedelta(years=1)
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
    sel_collection = collection_area.multiselect(
        label="Collections", options=collections, placeholder="Select product(s)"
    )
    sel_size = size_area.multiselect(
        label="Sizes", options=sizes, placeholder="Select size(s)"
    )
    sel_color = color_area.multiselect(
        label="Colors", options=colors, placeholder="Select color(s)"
    )

    combined, combined_previous, asin_sales, ads_visible, ads_previous = filtered_sales(
        sales.copy(),
        sessions.copy(),
        ads.copy(),
        forecast.copy(),
        sel_collection,
        sel_size,
        sel_color,
        available_inv,
        include_events,
        date_range,
        periods,
    )

    if not combined.empty:
        with plot_area:
            render_sales_chart(
                combined.copy(),
                ads_visible.copy(),
                show_change_notes=show_change_notes,
                show_lds=show_lds,
                available_inv=available_inv,
            )

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
        total_forecast_this_year = combined["forecast_units"].sum()

        # average numbers metrics
        days_this_year = (date_range[1] - date_range[0]).days + 1
        if not include_events:
            event_days = len(
                [x for x in event_dates_list if date_range[0] <= x <= date_range[1]]
            )
            days_this_year -= event_days
        days_last_year = (max_period - min_period).days + 1
        if not include_events:
            event_days_last_year = len(
                [x for x in event_dates_list if min_period <= x <= max_period]
            )
            days_last_year -= event_days_last_year

        average_units_this_year = combined["units"].sum() / days_this_year
        average_units_last_year = combined_previous["units"].sum() / days_last_year
        average_dollars_this_year = combined["net_sales"].sum() / days_this_year
        average_dollars_last_year = (
            combined_previous["net_sales"].sum() / days_last_year
        )
        average_sessions_this_year = combined["sessions"].sum() / days_this_year
        average_sessions_last_year = (
            combined_previous["sessions"].sum() / days_last_year
        )

        # ads metrics
        total_ad_units_this_year = ads_visible["total_units"].sum()
        total_ad_units_last_year = ads_previous["total_units"].sum()
        total_ad_dollars_this_year = ads_visible["total_sales"].sum()
        total_ad_dollars_last_year = ads_previous["total_sales"].sum()

        total_spend_this_year = ads_visible["ad_spend"].sum()
        total_spend_last_year = ads_previous["ad_spend"].sum()
        total_impressions_this_year = ads_visible["impressions"].sum()
        total_impressions_last_year = ads_previous["impressions"].sum()
        total_clicks_this_year = ads_visible["clicks"].sum()
        total_clicks_last_year = ads_previous["clicks"].sum()

        avg_conversion_this_year = (
            total_ad_units_this_year / total_clicks_this_year
            if total_clicks_this_year > 0
            else nan
        )
        avg_conversion_last_year = (
            total_ad_units_last_year / total_clicks_last_year
            if total_clicks_last_year > 0
            else nan
        )
        avg_cpc_this_year = (
            total_spend_this_year / total_clicks_this_year
            if total_clicks_this_year > 0
            else nan
        )
        avg_cpc_last_year = (
            total_spend_last_year / total_clicks_last_year
            if total_clicks_last_year > 0
            else nan
        )
        avg_acos_this_year = (
            total_spend_this_year / total_ad_dollars_this_year
            if total_ad_dollars_this_year > 0
            else nan
        )
        avg_acos_last_year = (
            total_spend_last_year / total_ad_dollars_last_year
            if total_ad_dollars_last_year > 0
            else nan
        )

        metric_text = (
            f"{min_period} - {max_period}"
            if periods == "custom"
            else f"compared to {periods}"
        )
        yoy_text = f"vs {periods}" if periods != "custom" else "vs period"

        units_metric.metric(
            label="Total units sold",
            value=f"{total_units_this_year:,.0f}",
            delta=f"{total_units_this_year / total_units_last_year -1:.1%} {yoy_text}",
            chart_data=combined["units"],
            help=f"{metric_text}: {total_units_last_year:,.0f}\nForecast units: {total_forecast_this_year:,.0f}",
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
            value=(
                f"{average_units_this_year:,.1f}"
                if average_units_this_year > 1
                else f"{average_units_this_year:.3f}"
            ),
            delta=f"{average_units_this_year / average_units_last_year -1:.1%} {yoy_text}",
            chart_data=combined["30-day avg"],
            help=(
                f"{metric_text}: {average_units_last_year:,.1f}"
                if average_units_last_year > 1
                else f"{metric_text}: {average_units_last_year:,.3f}"
            ),
        )
        avg_dollar_metric.metric(
            label="Avg sales/day",
            value=f"${average_dollars_this_year:,.0f}",
            delta=f"{average_dollars_this_year / average_dollars_last_year -1:.1%} {yoy_text}",
            chart_data=combined["30-day sales avg"],
            help=f"{metric_text}: ${average_dollars_last_year:,.0f}",
        )
        avg_sessions_metric.metric(
            label="Avg sessions/day",
            value=f"{average_sessions_this_year:,.0f}",
            delta=f"{average_sessions_this_year / average_sessions_last_year -1:.1%} {yoy_text}",
            chart_data=combined["30-day sessions avg"],
            help=f"{metric_text}: {average_sessions_last_year:,.0f}",
        )

        ad_units_metric.metric(
            label="Total ad units sold",
            value=f"{total_ad_units_this_year:,.0f}",
            delta=f"{total_ad_units_this_year / total_ad_units_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: {total_ad_units_last_year:,.0f}",
        )
        ad_sales_metric.metric(
            label="Total ad sales",
            value=f"${total_ad_dollars_this_year:,.0f}",
            delta=f"{total_ad_dollars_this_year / total_ad_dollars_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: ${total_ad_dollars_last_year:,.0f}",
        )
        ad_spend_metric.metric(
            label="Total ad spend",
            value=f"${total_spend_this_year:,.0f}",
            delta=f"{total_spend_this_year / total_spend_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: ${total_spend_last_year:,.0f}",
        )
        ad_impressions_metric.metric(
            label="Total ad impressions",
            value=f"{total_impressions_this_year:,.0f}",
            delta=f"{total_impressions_this_year / total_impressions_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: {total_impressions_last_year:,.0f}",
        )
        ad_clicks_metric.metric(
            label="Total ad clicks",
            value=f"{total_clicks_this_year:,.0f}",
            delta=f"{total_clicks_this_year / total_clicks_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: {total_clicks_last_year:,.0f}",
        )
        ad_conversion_metric.metric(
            label="Avg ad conversion %",
            value=f"{avg_conversion_this_year:.1%}",
            delta=f"{avg_conversion_this_year / avg_conversion_last_year -1:.1%} {yoy_text}",
            help=f"{metric_text}: {avg_conversion_last_year:.1%}",
        )
        ad_cpc_metric.metric(
            label="Avg CPC",
            value=f"${avg_cpc_this_year:.2f}",
            delta=f"{avg_cpc_this_year / avg_cpc_last_year -1:.1%} {yoy_text}",
            delta_color="inverse",
            help=f"{metric_text}: ${avg_cpc_last_year:.2f}",
        )
        ad_acos_metric.metric(
            label="Avg ACoS",
            value=f"{avg_acos_this_year:.1%}",
            delta=f"{avg_acos_this_year / avg_acos_last_year -1:.1%} {yoy_text}",
            delta_color="inverse",
            help=f"{metric_text}: {avg_acos_last_year:.1%}",
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


else:
    st.warning("No data available.")


def clear_data():
    if "sales" in st.session_state:
        del st.session_state["sales"]
    if "sessions" in st.session_state:
        del st.session_state["sessions"]
    if "ads" in st.session_state:
        del st.session_state["ads"]
    if os.path.exists(sales_tempfile):
        os.remove(sales_tempfile)
    if os.path.exists(sessions_tempfile):
        os.remove(sessions_tempfile)
    if os.path.exists(ads_tempfile):
        os.remove(ads_tempfile)
    if os.path.exists(forecast_tempfile) and wipe_forecast:
        os.remove(forecast_tempfile)


if st.user.email in ("2djohar@gmail.com", "sergey@mellanni.com"):
    wipe_forecast = st.checkbox("Wipe forecast data cache", value=False)

if st.button(
    "Refresh data",
    help="Clears cached data and pulls fresh data from source. Takes longer to load.",
):
    clear_data()
    st.rerun()
