from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from login import require_login
from modules import gcloud_modules as gc
from modules.gcloud_modules import bigquery

require_login()
st.set_page_config(
    page_title="Shopify units needed",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def pull_shopify_orders(start_date: str, end_date: str):
    query = """
    SELECT
        t1.id AS order_id,
        t1.name AS order_name,
        DATETIME(t1.created_at, 'America/Los_Angeles') AS order_date_pacific,
        line_item.sku AS sku,
        line_item.price AS sku_price,
        line_item.quantity AS sku_quantity,
        t1.fulfillment_status AS order_status
    FROM
        `mellanni-project-da.shopify.orders` AS t1,
        UNNEST(t1.line_items) AS line_item
    WHERE
        DATE(t1.created_at, 'America/Los_Angeles') BETWEEN @start_date AND @end_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )
    with gc.gcloud_connect() as client:
        result = client.query(query, job_config=job_config)

    return result


def pull_amazon_inventory(start_date: str, end_date: str):

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    query = """
        SELECT
            DATE(snapshot_date) AS date,
            sku,
            available as amz_available,
            Inventory_Supply_at_FBA AS amz_inventory,
        FROM
            `mellanni-project-da.reports.fba_inventory_planning`
        WHERE
            marketplace = 'US'
            AND DATE(snapshot_date) BETWEEN @start_date AND @end_date
        ORDER BY
            date DESC, sku ASC
    """

    with gc.gcloud_connect() as client:
        result = client.query(query, job_config=job_config)

    return result


def pull_wh_inventory(start_date: str, end_date: str):
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    wh_query = """
            SELECT
                date_date as date,
                ProductID AS sku,
                SUM(QtyAvailable) AS wh_inventory,
            FROM
                `mellanni-project-da.sellercloud.inventory_bins_partitioned`
            WHERE
                date_date  BETWEEN @start_date AND @end_date 
                AND Sellable = TRUE
                AND BinType != "Picking"
                AND NOT STARTS_WITH(BinName, "DS")
            GROUP BY
                date_date, ProductID
            """
    with gc.gcloud_connect() as client:
        result = client.query(wh_query, job_config=job_config)
    return result


def calculate_inventory_isr(date_from, date_to):
    inventory_job = pull_amazon_inventory(
        start_date=str(date_from), end_date=str(date_to)
    )
    wh_job = pull_wh_inventory(start_date=str(date_from), end_date=str(date_to))
    amazon_inventory = inventory_job.to_dataframe()
    wh_inventory = wh_job.to_dataframe()

    amazon_inventory["date"] = pd.to_datetime(amazon_inventory["date"]).dt.date
    wh_inventory["date"] = pd.to_datetime(wh_inventory["date"]).dt.date

    amazon_inventory["amz_inventory"] = pd.to_numeric(amazon_inventory["amz_inventory"])
    wh_inventory["wh_inventory"] = pd.to_numeric(wh_inventory["wh_inventory"])
    total_inventory = pd.merge(
        amazon_inventory, wh_inventory, how="outer", on=["date", "sku"], validate="1:1"
    ).fillna(0)
    total_inventory["total_inventory"] = total_inventory[
        ["amz_inventory", "wh_inventory"]
    ].sum(axis=1)

    inventory_grouped = (
        total_inventory.groupby(["date", "sku"])
        .agg({"total_inventory": "sum"})
        .reset_index()
    ).fillna(0)

    inventory_grouped["in-stock-rate"] = inventory_grouped["total_inventory"] > 0

    two_week_inventory = inventory_grouped.loc[
        pd.to_datetime(inventory_grouped["date"])
        >= pd.to_datetime(date_to) - timedelta(days=13)
    ]

    asin_isr_long_term = (
        inventory_grouped.pivot_table(
            values="in-stock-rate", index="sku", aggfunc="mean"
        )
        .round(2)
        .reset_index()
    )

    asin_isr_short_term = (
        two_week_inventory.pivot_table(
            values="in-stock-rate", index="sku", aggfunc="mean"
        )
        .round(2)
        .reset_index()
    )

    asin_isr_long_term = asin_isr_long_term.rename(columns={"in-stock-rate": "ISR"})
    asin_isr_short_term = asin_isr_short_term.rename(
        columns={"in-stock-rate": "ISR_short"}
    )
    asin_isr = pd.merge(
        asin_isr_long_term,
        asin_isr_short_term,
        on="sku",
        how="outer",
        validate="1:1",
    ).fillna(0)

    return asin_isr.fillna(0)


def calculate_orders(date_from, date_to, days_delta):
    order_job = pull_shopify_orders(start_date=str(date_from), end_date=str(date_to))

    shopify_orders = order_job.to_dataframe()
    shopify_orders["sku_price"] = pd.to_numeric(shopify_orders["sku_price"])
    shopify_orders["sku_quantity"] = pd.to_numeric(shopify_orders["sku_quantity"])

    orders_grouped = (
        shopify_orders.pivot_table(
            index="sku",
            values=["sku_quantity"],
            aggfunc=[
                lambda x: sum(x) / days_delta,
                lambda x: sum(x) / 14,
            ],
        )
        .fillna(0)
        .reset_index()
    )
    orders_grouped.columns = ["sku", "long-term avg", "short-term avg"]
    return orders_grouped


def process_data(date_from, date_to):
    with ThreadPoolExecutor() as executor:
        isr_job = executor.submit(calculate_inventory_isr, date_from, date_to)
        orders_job = executor.submit(
            calculate_orders, date_from, date_to, st.session_state["days_delta"]
        )

    # isr_data = calculate_inventory_isr(date_from, date_to)
    isr_data = isr_job.result()

    # orders_data = calculate_orders(date_from, date_to)
    orders_data = orders_job.result()

    combined = pd.merge(orders_data, isr_data, how="left", on="sku", validate="1:1")
    combined["long-term avg"] = (combined["long-term avg"] / combined["ISR"]).replace(
        [np.inf, -np.inf], 0
    )
    combined["short-term avg"] = (
        combined["short-term avg"] / combined["ISR_short"]
    ).replace([np.inf, -np.inf], 0)

    combined["avg corrected"] = (
        (0.6 * combined["short-term avg"]) + (0.4 * combined["long-term avg"])
    ).round(4)

    combined.loc[
        (combined["short-term avg"] / combined["long-term avg"]) > 5,
        "avg corrected",
    ] = (0.1 * combined["short-term avg"]) + (0.9 * combined["long-term avg"]).round(4)

    combined[f"Units needed for {st.session_state['days_of_sale']} days"] = (
        combined["avg corrected"] * st.session_state["days_of_sale"]
    )
    combined = combined.sort_values(
        f"Units needed for {st.session_state['days_of_sale']} days", ascending=False
    )
    return {"combined": combined, "isr_data": isr_data, "orders_data": orders_data}


#### INTERFACE ####
date_selector_area = st.container(vertical_alignment="center")
raw_df_area = st.container()
df_area = st.container()
date_from_col, date_to_col, days_of_sale_col, button_col = date_selector_area.columns(
    [3, 3, 2, 2]
)
date_from = date_from_col.date_input(
    label="start date", value=datetime.now() - timedelta(days=181)
)
date_to = date_to_col.date_input(
    label="end date",
    value=datetime.now() - timedelta(days=1),
    max_value=datetime.now() - timedelta(days=1),
)
days_of_sale = days_of_sale_col.number_input(
    label="days to cover", value=49, key="days_of_sale", width=100
)
st.session_state["days_delta"] = (date_to - date_from).days

if button_col.button("Get Data"):
    dfs = process_data(date_from, date_to)
    df_area.dataframe(
        dfs["combined"],
        hide_index=True,
        column_config={
            "ISR": st.column_config.NumberColumn(
                format="percent", help="long-term in-stock rate"
            ),
            "ISR_short": st.column_config.NumberColumn(
                format="percent", help="short-term in-stock rate"
            ),
        },
    )

    # raw_df_area.dataframe(dfs["isr_data"], hide_index=True)
    # raw_df_area.dataframe(dfs["orders_data"], hide_index=True)
