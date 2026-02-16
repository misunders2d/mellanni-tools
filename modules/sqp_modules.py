from datetime import datetime
from typing import Literal

import pandas as pd

from modules import gcloud_modules as gc
from modules.gcloud_modules import bigquery

asins = ["B00NLLUMOE", "B00NQDGAP2"]
start_date = ["2026-01-04", "2026-01-11"]
period = "WEEK"


def check_sqp_columns(sqp_raw: pd.DataFrame) -> dict:

    target_cols = {
        "startDate": "startDate",
        "endDate": "endDate",
        "asin": "asin",
        "searchQueryData_searchQuery": "searchQuery",
        "searchQueryData_searchQueryScore": "searchQueryScore",
        "searchQueryData_searchQueryVolume": "searchQueryVolume",
        "impressionData_totalQueryImpressionCount": "totalQueryImpressionCount",
        "impressionData_asinImpressionCount": "asinImpressionCount",
        "impressionData_asinImpressionShare": "asinImpressionShare",
        "clickData_totalClickCount": "totalClickCount",
        "clickData_totalClickRate": "totalClickRate",
        "clickData_asinClickCount": "asinClickCount",
        "clickData_asinClickShare": "asinClickShare",
        "totalMedianClickPrice_amount": "totalMedianClickPrice_amount",
        "totalMedianClickPrice_currencyCode": "totalMedianClickPrice_currencyCode",
        "asinMedianClickPrice_amount": "asinMedianClickPrice_amount",
        "asinMedianClickPrice_currencyCode": "asinMedianClickPrice_currencyCode",
        "clickData_totalSameDayShippingClickCount": "totalSameDayShippingClickCount",
        "clickData_totalOneDayShippingClickCount": "totalOneDayShippingClickCount",
        "clickData_totalTwoDayShippingClickCount": "totalTwoDayShippingClickCount",
        "cartAddData_totalCartAddCount": "totalCartAddCount",
        "cartAddData_totalCartAddRate": "totalCartAddRate",
        "cartAddData_asinCartAddCount": "asinCartAddCount",
        "cartAddData_asinCartAddShare": "asinCartAddShare",
        "totalMedianCartAddPrice_amount": "totalMedianCartAddPrice_amount",
        "totalMedianCartAddPrice_currencyCode": "totalMedianCartAddPrice_currencyCode",
        "asinMedianCartAddPrice_amount": "asinMedianCartAddPrice_amount",
        "asinMedianCartAddPrice_currencyCode": "asinMedianCartAddPrice_currencyCode",
        "cartAddData_totalSameDayShippingCartAddCount": "totalSameDayShippingCartAddCount",
        "cartAddData_totalOneDayShippingCartAddCount": "totalOneDayShippingCartAddCount",
        "cartAddData_totalTwoDayShippingCartAddCount": "totalTwoDayShippingCartAddCount",
        "purchaseData_totalPurchaseCount": "totalPurchaseCount",
        "purchaseData_totalPurchaseRate": "totalPurchaseRate",
        "purchaseData_asinPurchaseCount": "asinPurchaseCount",
        "purchaseData_asinPurchaseShare": "asinPurchaseShare",
        "totalMedianPurchasePrice_amount": "totalMedianPurchasePrice_amount",
        "totalMedianPurchasePrice_currencyCode": "totalMedianPurchasePrice_currencyCode",
        "asinMedianPurchasePrice_amount": "asinMedianPurchasePrice_amount",
        "asinMedianPurchasePrice_currencyCode": "asinMedianPurchasePrice_currencyCode",
        "purchaseData_totalSameDayShippingPurchaseCount": "totalSameDayShippingPurchaseCount",
        "purchaseData_totalOneDayShippingPurchaseCount": "totalOneDayShippingPurchaseCount",
        "purchaseData_totalTwoDayShippingPurchaseCount": "totalTwoDayShippingPurchaseCount",
        "cartAddData_asinMedianCartAddPrice": "asinMedianCartAddPrice",
        "purchaseData_asinMedianPurchasePrice": "asinMedianPurchasePrice",
        "clickData_asinMedianClickPrice": "asinMedianClickPrice",
        "cartAddData_totalMedianCartAddPrice": "totalMedianCartAddPrice",
        "purchaseData_totalMedianPurchasePrice": "totalMedianPurchasePrice",
        "clickData_totalMedianClickPrice": "totalMedianClickPrice",
        "period": "period",
        "marketplaces": "marketplaces",
    }
    if not sqp_raw.columns.tolist() == list(target_cols.keys()):
        wrong_cols = [
            x for x in sqp_raw.columns.tolist() if x not in list(target_cols.keys())
        ] or [x for x in list(target_cols.keys()) if x not in sqp_raw.columns.tolist()]
        return {"status": "error", "message": ", ".join(wrong_cols)}

        sum_cols = [
            "asinImpressionCount",
            "asinImpressionShare",
            "asinClickCount",
            "asinClickShare",
            "totalMedianClickPrice_amount",
            "totalMedianClickPrice_currencyCode",
            "asinMedianClickPrice_amount",
            "asinMedianClickPrice_currencyCode",
            "totalSameDayShippingClickCount",
            "totalOneDayShippingClickCount",
            "totalTwoDayShippingClickCount",
            "totalCartAddCount",
            "totalCartAddRate",
            "asinCartAddCount",
            "asinCartAddShare",
            "totalMedianCartAddPrice_amount",
            "totalMedianCartAddPrice_currencyCode",
            "asinMedianCartAddPrice_amount",
            "asinMedianCartAddPrice_currencyCode",
            "totalSameDayShippingCartAddCount",
            "totalOneDayShippingCartAddCount",
            "totalTwoDayShippingCartAddCount",
            "totalPurchaseCount",
            "totalPurchaseRate",
            "asinPurchaseCount",
            "asinPurchaseShare",
            "totalMedianPurchasePrice_amount",
            "totalMedianPurchasePrice_currencyCode",
            "asinMedianPurchasePrice_amount",
            "asinMedianPurchasePrice_currencyCode",
            "totalSameDayShippingPurchaseCount",
            "totalOneDayShippingPurchaseCount",
            "totalTwoDayShippingPurchaseCount",
            "asinMedianCartAddPrice",
            "asinMedianPurchasePrice",
            "asinMedianClickPrice",
            "totalMedianCartAddPrice",
            "totalMedianPurchasePrice",
            "totalMedianClickPrice",
        ]

        immutable_cols = [
            "startDate",
            "endDate",
            "asin",
            "searchQuery",
            "searchQueryScore",
            "searchQueryVolume",
            "totalQueryImpressionCount",
            "asinImpressionCount",
            "asinImpressionShare",
            "totalClickCount",
            "totalClickRate",
            "asinClickCount",
            "asinClickShare",
            "totalMedianClickPrice_amount",
            "totalMedianClickPrice_currencyCode",
            "asinMedianClickPrice_amount",
            "asinMedianClickPrice_currencyCode",
            "totalSameDayShippingClickCount",
            "totalOneDayShippingClickCount",
            "totalTwoDayShippingClickCount",
            "totalCartAddCount",
            "totalCartAddRate",
            "asinCartAddCount",
            "asinCartAddShare",
            "totalMedianCartAddPrice_amount",
            "totalMedianCartAddPrice_currencyCode",
            "asinMedianCartAddPrice_amount",
            "asinMedianCartAddPrice_currencyCode",
            "totalSameDayShippingCartAddCount",
            "totalOneDayShippingCartAddCount",
            "totalTwoDayShippingCartAddCount",
            "totalPurchaseCount",
            "totalPurchaseRate",
            "asinPurchaseCount",
            "asinPurchaseShare",
            "totalMedianPurchasePrice_amount",
            "totalMedianPurchasePrice_currencyCode",
            "asinMedianPurchasePrice_amount",
            "asinMedianPurchasePrice_currencyCode",
            "totalSameDayShippingPurchaseCount",
            "totalOneDayShippingPurchaseCount",
            "totalTwoDayShippingPurchaseCount",
            "asinMedianCartAddPrice",
            "asinMedianPurchasePrice",
            "asinMedianClickPrice",
            "totalMedianCartAddPrice",
            "totalMedianPurchasePrice",
            "totalMedianClickPrice",
            "period",
            "marketplaces",
        ]

    return {"status": "success", "message": target_cols}


def check_if_not_sundays(date: list[str] | str) -> list:
    date_clean = (
        [datetime.strptime(date, "%Y-%m-%d").date()]
        if isinstance(date, str)
        else [datetime.strptime(x, "%Y-%m-%d").date() for x in date]
    )
    not_sundays = list(filter(lambda x: x.weekday() != 6, date_clean))
    return not_sundays


def pull_sqp_asin_data(
    asins: list[str] | str,
    start_date: list[str] | str,
    period: Literal["WEEK", "MONTH"] = "WEEK",
) -> dict[str, pd.DataFrame | str]:
    try:
        asins = [asins] if isinstance(asins, str) else asins
        start_date_clean = (
            [datetime.strptime(start_date, "%Y-%m-%d").date()]
            if isinstance(start_date, str)
            else [datetime.strptime(x, "%Y-%m-%d").date() for x in start_date]
        )

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("asins", "STRING", asins),
                bigquery.ArrayQueryParameter(
                    "start_date_clean", "DATE", start_date_clean
                ),
                bigquery.ScalarQueryParameter("period", "STRING", period),
            ]
        )

        query = """
        SELECT *
            FROM `mellanni-project-da.auxillary_development.sqp_asin_weekly`
            WHERE asin IN UNNEST(@asins)
            AND DATE(startDate) IN UNNEST(@start_date_clean)
            AND period = @period
        """

        with gc.gcloud_connect() as client:
            result = client.query(query, job_config=job_config)
        sqp_raw = result.to_dataframe()
        return {"status": "success", "result": sqp_raw}
    except Exception as e:
        return {"status": "error", "result": str(e)}


def calculate_sqp(sqp_raw: pd.DataFrame):
    column_check = check_sqp_columns(sqp_raw)
    if column_check.get("status") == "error":
        raise BaseException(f"Columns do not match: {column_check.get('message')}")
    sqp_raw = sqp_raw.rename(columns=column_check.get("message"))
