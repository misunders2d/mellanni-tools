import os
import re

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import streamlit as st
from common.events import event_dates_list, events
from dateutil.relativedelta import relativedelta
from google.cloud import bigquery
from google.oauth2 import service_account

from login import require_login, require_role
from modules.filter_modules import filter_dictionary
from modules.sales_charts import render_sales_chart
from modules.sales_trends import SalesTrendsData, metric_delta, metric_value, safe_ratio

os.makedirs("temp", exist_ok=True)

sales_tempfile = os.path.join("temp", "sales.parquet")
sessions_tempfile = os.path.join("temp", "sessions.parquet")
ads_tempfile = os.path.join("temp", "ads.parquet")
forecast_tempfile = os.path.join("temp", "forecast.parquet")

st.set_page_config(
    page_title="Sales history", page_icon="media/logo.ico", layout="wide"
)

require_login()

GC_CREDENTIALS = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)

require_role("admin", "sales")

collection_area, size_area, color_area, sku_area = st.columns([2, 1, 1, 2])
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
ad_metrics_area2.caption(
    "Sponsored Products · 14-day click attribution · filtered by advertised ASIN."
)
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
                SUM(COALESCE(item_price,0)) - SUM(COALESCE(item_promotion_discount,0)) AS net_sales
            FROM mellanni-project-da.reports.all_orders
            WHERE DATE(purchase_date, "America/Los_Angeles") >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
                AND LOWER(sales_channel) = 'amazon.com'
            GROUP BY date, asin
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
            deduped_sku_dict AS (
            SELECT
                sku,
                ARRAY_AGG(asin IGNORE NULLS ORDER BY asin LIMIT 1)[SAFE_OFFSET(0)] AS asin
            FROM mellanni-project-da.auxillary_development.dictionary
            WHERE sku IS NOT NULL
            GROUP BY sku
            ),
            changelog_mapped AS (
            SELECT
                DATE(sc.date) AS date,
                sd.asin,
                sc.change_type,
                sc.notes
            FROM mellanni-project-da.auxillary_development.sku_changelog sc
            LEFT JOIN deduped_sku_dict sd
                ON sc.sku = sd.sku
            WHERE DATE(sc.date) >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
            ),
            changelog_agg AS (
            SELECT
                date,
                asin,
                STRING_AGG(
                    DISTINCT IF(
                        NULLIF(TRIM(COALESCE(notes, '')), '') IS NULL,
                        COALESCE(change_type, ''),
                        CONCAT(COALESCE(change_type, ''), ': ', notes)
                    ),
                    ' | '
                ) AS change_notes
            FROM changelog_mapped
            WHERE asin IS NOT NULL
            GROUP BY date, asin
            ),
            sales_with_changelog AS (
            SELECT
                COALESCE(s.date, ca.date) AS date,
                COALESCE(s.asin, ca.asin) AS asin,
                COALESCE(s.units, 0) AS units,
                COALESCE(s.net_sales, 0) AS net_sales,
                s.asin IS NOT NULL AS has_sales_row,
                ca.change_notes
            FROM sales s
            FULL OUTER JOIN changelog_agg ca
                ON s.date = ca.date
                AND s.asin = ca.asin
            ),
            sales_with_inventory AS (
            SELECT
                COALESCE(s.date, inv.date) AS date,
                COALESCE(s.asin, inv.asin) AS asin,
                COALESCE(s.units, 0) AS units,
                COALESCE(s.net_sales, 0) AS net_sales,
                COALESCE(s.has_sales_row, FALSE) AS has_sales_row,
                inv.asin IS NOT NULL AS has_inventory_row,
                inv.inventory_supply_at_fba,
                inv.available,
                s.change_notes
            FROM sales_with_changelog s
            FULL OUTER JOIN inventory_by_date_asin inv
                ON s.date = inv.date
                AND s.asin = inv.asin
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
            s.inventory_supply_at_fba,
            s.available,
            s.has_sales_row,
            s.has_inventory_row,
            s.change_notes
            FROM sales_with_inventory s
            LEFT JOIN deduped_asin_dict d
            ON s.asin = d.asin
            ORDER BY s.date ASC, s.units DESC
            """

    sessions_query = f"""
            SELECT
                DATE(date) AS date,
                childAsin AS asin,
                SUM(sessions) AS sessions
            FROM mellanni-project-da.reports.business_report_asin
            WHERE DATE(date) >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
                AND LOWER(country_code) = 'us'
            GROUP BY date, asin
            ORDER BY date ASC
            """

    ads_query = f"""
            SELECT
                DATE(date) AS date,
                advertisedAsin AS asin,
                SUM(spend) AS ad_spend,
                SUM(impressions) AS impressions,
                SUM(clicks) AS clicks,
                SUM(unitsSoldClicks14d) AS total_units,
                SUM(sales14d) AS total_sales
            FROM mellanni-project-da.reports.AdvertisedProduct
            WHERE DATE(date) >= DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {interval})
                AND LOWER(country_code) = 'us'
            GROUP BY date, asin
            ORDER BY date ASC, asin
    """

    forecast_query = "SELECT date, asin, units as forecast_units, dollar as forecast_dollar FROM mellanni-project-da.daily_reports.forecast ORDER BY date, asin"
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


def _top_n_sellers(asin_sales: pd.DataFrame, num_top_sellers: int) -> pd.DataFrame:
    asin_sales = asin_sales.head(num_top_sellers).reset_index(drop=True).copy()
    totals_asins = asin_sales.sum(numeric_only=True, axis=0)
    asin_sales.loc[:, "#"] = asin_sales.index + 1
    asin_sales = pd.concat([asin_sales, pd.DataFrame(totals_asins).T])
    return asin_sales


@st.cache_resource(max_entries=1, show_spinner="Preparing sales history...")
def load_sales_snapshot():
    paths = (sales_tempfile, sessions_tempfile, ads_tempfile, forecast_tempfile)
    required = {"change_notes", "has_sales_row", "has_inventory_row"}
    cache_valid = all(os.path.exists(path) for path in paths)
    if cache_valid:
        try:
            # Version every file so old attribution cannot silently reuse
            # incompatible source data.
            schemas = [pq.read_schema(path) for path in paths]
            generation = (schemas[0].metadata or {}).get(b"sales_trends_generation")
            cache_valid = (
                generation is not None
                and required.issubset(schemas[0].names)
                and all(
                    (schema.metadata or {}).get(b"sales_trends_version") == b"2"
                    and (schema.metadata or {}).get(b"sales_trends_generation") == generation
                    for schema in schemas
                )
            )
        except (OSError, pa.ArrowInvalid):
            cache_valid = False
    if not cache_valid:
        fresh = get_sales_data()
        if any(frame is None for frame in fresh):
            return None
        generation = os.urandom(16)
        for frame, path in zip(fresh, paths):
            table = pa.Table.from_pandas(frame, preserve_index=False)
            metadata = {
                **(table.schema.metadata or {}), b"sales_trends_version": b"2",
                b"sales_trends_generation": generation,
            }
            temporary = f"{path}.{generation.hex()}.tmp"
            try:
                pq.write_table(table.replace_schema_metadata(metadata), temporary)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)
        del fresh, frame, table
    return SalesTrendsData("temp", events, event_dates_list)


# Release copies retained by sessions opened before this optimization.
for key in ("sales", "sessions", "ads", "forecast"):
    st.session_state.pop(key, None)
snapshot = load_sales_snapshot()

if snapshot is not None and not snapshot.frames[0].empty:
    min_date, max_date = snapshot.date_bounds
    cached_at = snapshot.cached_at.tz_convert("America/Los_Angeles")
    st.caption(f"Data refreshed {cached_at:%b %d, %Y %H:%M %Z}. Use Refresh data to reload.")
    date_range = (
        date_from_picker.date_input(
            "Start date",
            value=max(min_date, max_date - pd.Timedelta(days=90)),
            min_value=min_date,
            max_value=max_date,
            width=150,
        ),
        date_to_picker.date_input(
            "End date",
            value=max_date,
            min_value=min_date,
            max_value=max(
                max_date, pd.to_datetime(f"{pd.to_datetime('today').year}-12-31").date()
            ),
            width=150,
        ),
    )

    with st.sidebar:
        options = ["last year", "custom", "prior event"]
        if (date_range[1] - date_range[0]).days == 6:
            options = ["last week", "last year", "custom", "prior event"]
        periods = st.radio("Compare periods", options=options)
        min_period, max_period = (
            date_range[0] - relativedelta(years=1),
            date_range[1] - relativedelta(years=1),
        )
        if periods == "last week":
            min_period = date_range[0] - relativedelta(weeks=1)
            max_period = date_range[1] - relativedelta(weeks=1)
        elif periods == "custom":
            min_period = st.date_input(
                "Date from", value=max_date - relativedelta(years=1, days=90)
            )
            max_period = st.date_input(
                "Date to", value=max_date - relativedelta(years=1)
            )
        elif periods == "prior event":
            available_events = [
                name
                for name, (_start, end) in events.items()
                if pd.Timestamp(end) <= pd.Timestamp(max_date)
            ]
            event_name = st.selectbox(
                "Event",
                options=(
                    sorted(available_events, key=lambda n: events[n][0])
                    or sorted(events.keys(), key=lambda n: events[n][0])
                ),
                key="prior_event_select",
            )
            min_period = pd.Timestamp(events[event_name][0]).date()
            max_period = pd.Timestamp(events[event_name][1]).date()
            st.caption(f"{min_period:%b %d, %Y} – {max_period:%b %d, %Y}")
            periods = event_name

    include_events = events_checkbox.checkbox("Include events?", value=True)
    show_change_notes = changes_checkbox.checkbox("Show change notes?", value=True)
    show_lds = lds_checkbox.checkbox("Show LDs/BDs?", value=False)
    available_inv = inv_checkbox.checkbox("Show only available inventory", value=True)

    sku_text = sku_area.text_area(
        "Filter by SKU / ASIN",
        placeholder="Paste SKUs or ASINs (one per line or comma-separated)",
        height=68,
        key="sales_trends_sku_filter",
        help="When populated, collection/size/color selectors are ignored.",
    )
    # Split on any mix of commas / whitespace / newlines / tabs.
    sku_tokens = [t for t in re.split(r"[,\s]+", sku_text) if t]
    unique_tokens = list(dict.fromkeys(sku_tokens))

    filtered_dict = filter_dictionary(
        coll_target=collection_area,
        size_target=size_area,
        color_target=color_area,
        disabled=bool(sku_tokens),
    )
    if sku_tokens:
        full_dict = st.session_state.dictionary
        sku_match = full_dict["sku"].isin(unique_tokens)
        asin_match = full_dict["asin"].isin(unique_tokens)
        filtered_dict = full_dict.loc[sku_match | asin_match]
        matched_tokens = {
            t
            for t in unique_tokens
            if t in full_dict["sku"].values or t in full_dict["asin"].values
        }
        unmatched = [t for t in unique_tokens if t not in matched_tokens]
        caption = (
            f"Matched {len(matched_tokens)} of {len(unique_tokens)} pasted token(s)"
        )
        if unmatched:
            preview = ", ".join(unmatched[:5])
            if len(unmatched) > 5:
                preview += f", +{len(unmatched) - 5} more"
            caption += f". Unmatched: {preview}"
        sku_area.caption(caption)
        target_asins = filtered_dict["asin"].dropna().unique().tolist()
    elif (
        st.session_state.get("sel_col")
        or st.session_state.get("sel_size")
        or st.session_state.get("sel_color")
    ):
        target_asins = filtered_dict["asin"].dropna().unique().tolist()
    else:
        target_asins = None

    combined, combined_previous, asin_sales, ads_visible, ads_previous = snapshot.query(
        target_asins,
        available_inv,
        include_events,
        date_range,
        periods,
        (min_period, max_period),
    )

    if not combined.empty:
        with plot_area:
            render_sales_chart(
                combined,
                ads_visible,
                show_change_notes=show_change_notes,
                show_lds=show_lds,
                available_inv=available_inv,
            )

        # absolute numbers metrics
        total_units_this_year = combined["units"].sum(min_count=1)
        total_units_last_year = combined_previous["units"].sum(min_count=1)
        total_dollars_this_year = combined["net_sales"].sum(min_count=1)
        total_dollars_last_year = combined_previous["net_sales"].sum(min_count=1)
        average_price_this_year = safe_ratio(total_dollars_this_year, total_units_this_year)
        average_price_last_year = safe_ratio(total_dollars_last_year, total_units_last_year)
        sessions_this_year = combined["sessions"].sum(min_count=1)
        sessions_last_year = combined_previous["sessions"].sum(min_count=1)
        conversion_this_year = safe_ratio(total_units_this_year, sessions_this_year)
        conversion_last_year = safe_ratio(total_units_last_year, sessions_last_year)
        total_forecast_this_year = combined["forecast_units"].sum(min_count=1)
        total_dollar_forecast_this_year = combined["forecast_dollar"].sum(min_count=1)

        # Missing future/source dates and excluded events are NaN. Observed
        # calendar days with zero sales remain zero and count in these averages.
        average_units_this_year = combined["units"].mean()
        average_units_last_year = combined_previous["units"].mean()
        average_dollars_this_year = combined["net_sales"].mean()
        average_dollars_last_year = combined_previous["net_sales"].mean()
        average_sessions_this_year = combined["sessions"].mean()
        average_sessions_last_year = combined_previous["sessions"].mean()

        # ads metrics
        total_ad_units_this_year = ads_visible["total_units"].sum(min_count=1)
        total_ad_units_last_year = ads_previous["total_units"].sum(min_count=1)
        total_ad_dollars_this_year = ads_visible["total_sales"].sum(min_count=1)
        total_ad_dollars_last_year = ads_previous["total_sales"].sum(min_count=1)

        total_spend_this_year = ads_visible["ad_spend"].sum(min_count=1)
        total_spend_last_year = ads_previous["ad_spend"].sum(min_count=1)
        total_impressions_this_year = ads_visible["impressions"].sum(min_count=1)
        total_impressions_last_year = ads_previous["impressions"].sum(min_count=1)
        total_clicks_this_year = ads_visible["clicks"].sum(min_count=1)
        total_clicks_last_year = ads_previous["clicks"].sum(min_count=1)

        avg_conversion_this_year = safe_ratio(total_ad_units_this_year, total_clicks_this_year)
        avg_conversion_last_year = safe_ratio(total_ad_units_last_year, total_clicks_last_year)
        avg_cpc_this_year = safe_ratio(total_spend_this_year, total_clicks_this_year)
        avg_cpc_last_year = safe_ratio(total_spend_last_year, total_clicks_last_year)
        avg_acos_this_year = safe_ratio(total_spend_this_year, total_ad_dollars_this_year)
        avg_acos_last_year = safe_ratio(total_spend_last_year, total_ad_dollars_last_year)

        metric_text = (
            f"{min_period} - {max_period}"
            if periods == "custom"
            else f"compared to {periods}"
        )
        yoy_text = f"vs {periods}" if periods != "custom" else "vs period"

        units_metric.metric(
            label="Total units sold",
            value=metric_value(total_units_this_year, ',.0f'),
            delta=metric_delta(total_units_this_year, total_units_last_year, yoy_text),
            chart_data=combined["units"],
            help=f"{metric_text}: {metric_value(total_units_last_year, ',.0f')}\nForecast units: {metric_value(total_forecast_this_year, ',.0f')}",
        )
        dollar_metric.metric(
            label="Total sales",
            value=metric_value(total_dollars_this_year, ',.0f', '$'),
            delta=metric_delta(total_dollars_this_year, total_dollars_last_year, yoy_text),
            chart_data=combined["net_sales"],
            help=f"{metric_text}: {metric_value(total_dollars_last_year, ',.0f', '$')}\nForecast sales: {metric_value(total_dollar_forecast_this_year, ',.0f')}",
        )
        price_metric.metric(
            label="Average price",
            value=metric_value(average_price_this_year, ',.2f', '$'),
            delta=metric_delta(average_price_this_year, average_price_last_year, yoy_text),
            chart_data=combined["average selling price"],
            help=f"{metric_text}: {metric_value(average_price_last_year, ',.2f', '$')}",
        )
        sessions_metric.metric(
            label="Total sessions",
            value=metric_value(sessions_this_year, ',.0f'),
            delta=metric_delta(sessions_this_year, sessions_last_year, yoy_text),
            chart_data=combined["sessions"],
            help=f"{metric_text}: {metric_value(sessions_last_year, ',.0f')}",
        )
        conversion_metric.metric(
            label="Conversion %",
            value=metric_value(conversion_this_year, '.1%'),
            delta=metric_delta(conversion_this_year, conversion_last_year, yoy_text),
            chart_data=(combined["units"].div(combined["sessions"].where(combined["sessions"] > 0)) * 100).round(1),
            help=f"{metric_text}: {metric_value(conversion_last_year, '.1%')}",
        )

        avg_units_metric.metric(
            label="Avg units/day",
            value=(
                metric_value(average_units_this_year, ',.1f')
                if pd.notna(average_units_this_year) and average_units_this_year > 1
                else metric_value(average_units_this_year, '.3f')
            ),
            delta=metric_delta(average_units_this_year, average_units_last_year, yoy_text),
            chart_data=combined["30-day avg"],
            help=(
                f"{metric_text}: {metric_value(average_units_last_year, ',.1f')}"
                if pd.notna(average_units_last_year) and average_units_last_year > 1
                else f"{metric_text}: {metric_value(average_units_last_year, ',.3f')}"
            ),
        )
        avg_dollar_metric.metric(
            label="Avg sales/day",
            value=metric_value(average_dollars_this_year, ',.0f', '$'),
            delta=metric_delta(average_dollars_this_year, average_dollars_last_year, yoy_text),
            chart_data=combined["30-day sales avg"],
            help=f"{metric_text}: {metric_value(average_dollars_last_year, ',.0f', '$')}",
        )
        avg_sessions_metric.metric(
            label="Avg sessions/day",
            value=metric_value(average_sessions_this_year, ',.0f'),
            delta=metric_delta(average_sessions_this_year, average_sessions_last_year, yoy_text),
            chart_data=combined["30-day sessions avg"],
            help=f"{metric_text}: {metric_value(average_sessions_last_year, ',.0f')}",
        )

        ad_units_metric.metric(
            label="Total ad units sold",
            value=metric_value(total_ad_units_this_year, ',.0f'),
            delta=metric_delta(total_ad_units_this_year, total_ad_units_last_year, yoy_text),
            help=f"{metric_text}: {metric_value(total_ad_units_last_year, ',.0f')}",
        )
        ad_sales_metric.metric(
            label="Total ad sales",
            value=metric_value(total_ad_dollars_this_year, ',.0f', '$'),
            delta=metric_delta(total_ad_dollars_this_year, total_ad_dollars_last_year, yoy_text),
            help=f"{metric_text}: {metric_value(total_ad_dollars_last_year, ',.0f', '$')}",
        )
        ad_spend_metric.metric(
            label="Total ad spend",
            value=metric_value(total_spend_this_year, ',.0f', '$'),
            delta=metric_delta(total_spend_this_year, total_spend_last_year, yoy_text),
            help=f"{metric_text}: {metric_value(total_spend_last_year, ',.0f', '$')}",
        )
        ad_impressions_metric.metric(
            label="Total ad impressions",
            value=metric_value(total_impressions_this_year, ',.0f'),
            delta=metric_delta(total_impressions_this_year, total_impressions_last_year, yoy_text),
            help=f"{metric_text}: {metric_value(total_impressions_last_year, ',.0f')}",
        )
        ad_clicks_metric.metric(
            label="Total ad clicks",
            value=metric_value(total_clicks_this_year, ',.0f'),
            delta=metric_delta(total_clicks_this_year, total_clicks_last_year, yoy_text),
            help=f"{metric_text}: {metric_value(total_clicks_last_year, ',.0f')}",
        )
        ad_conversion_metric.metric(
            label="Avg ad conversion %",
            value=metric_value(avg_conversion_this_year, '.1%'),
            delta=metric_delta(avg_conversion_this_year, avg_conversion_last_year, yoy_text),
            help=f"{metric_text}: {metric_value(avg_conversion_last_year, '.1%')}",
        )
        ad_cpc_metric.metric(
            label="Avg CPC",
            value=metric_value(avg_cpc_this_year, '.2f', '$'),
            delta=metric_delta(avg_cpc_this_year, avg_cpc_last_year, yoy_text),
            delta_color="inverse",
            help=f"{metric_text}: {metric_value(avg_cpc_last_year, '.2f', '$')}",
        )
        ad_acos_metric.metric(
            label="Avg ACoS",
            value=metric_value(avg_acos_this_year, '.1%'),
            delta=metric_delta(avg_acos_this_year, avg_acos_last_year, yoy_text),
            delta_color="inverse",
            help=f"{metric_text}: {metric_value(avg_acos_last_year, '.1%')}",
        )

        num_top_sellers = df_top_sellers.number_input(
            "Select top n sellers", min_value=2, max_value=10000, value=10, width=150
        )
        df_text.text(f"Top {num_top_sellers} sellers")
        asin_sales_top = _top_n_sellers(asin_sales, num_top_sellers)
        asin_sales_top["asin"] = "https://www.amazon.com/dp/" + asin_sales_top["asin"]
        asin_sales_top["conversion"] = asin_sales_top["units"].div(
            asin_sales_top["sessions"].where(asin_sales_top["sessions"] > 0)
        )
        df_area_container.data_editor(
            asin_sales_top,
            num_rows="fixed",
            hide_index=True,
            column_order=[
                "#",
                "asin",
                "collection",
                "size",
                "color",
                "units",
                "net_sales",
                "sales_share",
                "sessions",
                "conversion",
                "available",
                "inventory_supply_at_fba",
            ],
            column_config={
                "#": st.column_config.NumberColumn(),
                "asin": st.column_config.LinkColumn(
                    display_text="https://www\\.amazon\\.com/dp/(.*)"
                ),
                "units": st.column_config.NumberColumn(format="localized"),
                "net_sales": st.column_config.NumberColumn(format="dollar"),
                "sales_share": st.column_config.NumberColumn(format="percent"),
                "conversion": st.column_config.NumberColumn(format="percent"),
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
    load_sales_snapshot.clear()


wipe_forecast = False
if st.user.email in ("2djohar@gmail.com", "sergey@mellanni.com"):
    wipe_forecast = st.checkbox("Wipe forecast data cache", value=False)

if st.button(
    "Refresh data",
    help="Clears cached data and pulls fresh data from source. Takes longer to load.",
):
    clear_data()
    st.rerun()
