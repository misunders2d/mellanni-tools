from datetime import datetime
from typing import Literal

import pandas as pd
from utils.mellanni_modules import export_to_excel, user_folder

from modules import gcloud_modules as gc
from modules.gcloud_modules import bigquery

asins = ["B00NLLUMOE", "B00NQDGAP2", "B0822XBDZW"]
start_date = ["2026-01-04", "2026-01-11", "2026-02-01", "2026-02-08", "2026-02-20"]
period = "WEEK"


def check_sqp_columns(sqp_raw: pd.DataFrame) -> dict:

    target_cols = {
        "startDate": ("startDate", {"type": ""}),
        "endDate": ("endDate", {"type": ""}),
        "asin": ("asin", {"type": ""}),
        "searchQueryData_searchQuery": ("searchQuery", {"type": ""}),
        "searchQueryData_searchQueryScore": ("searchQueryScore", {"type": ""}),
        "searchQueryData_searchQueryVolume": ("searchQueryVolume", {"type": "number"}),
        "impressionData_totalQueryImpressionCount": (
            "totalQueryImpressionCount",
            {"type": "number"},
        ),
        "impressionData_asinImpressionCount": (
            "asinImpressionCount",
            {"type": "number"},
        ),
        "impressionData_asinImpressionShare": (
            "asinImpressionShare",
            {"type": "percent", "precision": 2},
        ),
        "clickData_totalClickCount": ("totalClickCount", {"type": "number"}),
        "clickData_totalClickRate": ("totalClickRate", {"type": "percent"}),
        "clickData_asinClickCount": ("asinClickCount", {"type": "number"}),
        "clickData_asinClickShare": ("asinClickShare", {"type": "percent"}),
        "totalMedianClickPrice_amount": (
            "totalMedianClickPrice_amount",
            {"type": "currency"},
        ),
        "totalMedianClickPrice_currencyCode": (
            "totalMedianClickPrice_currencyCode",
            {"type": ""},
        ),
        "asinMedianClickPrice_amount": (
            "asinMedianClickPrice_amount",
            {"type": "currency"},
        ),
        "asinMedianClickPrice_currencyCode": (
            "asinMedianClickPrice_currencyCode",
            {"type": ""},
        ),
        "clickData_totalSameDayShippingClickCount": (
            "totalSameDayShippingClickCount",
            {"type": "number"},
        ),
        "clickData_totalOneDayShippingClickCount": (
            "totalOneDayShippingClickCount",
            {"type": "number"},
        ),
        "clickData_totalTwoDayShippingClickCount": (
            "totalTwoDayShippingClickCount",
            {"type": "number"},
        ),
        "cartAddData_totalCartAddCount": ("totalCartAddCount", {"type": "number"}),
        "cartAddData_totalCartAddRate": ("totalCartAddRate", {"type": "percent"}),
        "cartAddData_asinCartAddCount": ("asinCartAddCount", {"type": "number"}),
        "cartAddData_asinCartAddShare": ("asinCartAddShare", {"type": "percent"}),
        "totalMedianCartAddPrice_amount": (
            "totalMedianCartAddPrice_amount",
            {"type": "currency"},
        ),
        "totalMedianCartAddPrice_currencyCode": (
            "totalMedianCartAddPrice_currencyCode",
            {"type": ""},
        ),
        "asinMedianCartAddPrice_amount": (
            "asinMedianCartAddPrice_amount",
            {"type": "currency"},
        ),
        "asinMedianCartAddPrice_currencyCode": (
            "asinMedianCartAddPrice_currencyCode",
            {"type": ""},
        ),
        "cartAddData_totalSameDayShippingCartAddCount": (
            "totalSameDayShippingCartAddCount",
            {"type": "number"},
        ),
        "cartAddData_totalOneDayShippingCartAddCount": (
            "totalOneDayShippingCartAddCount",
            {"type": "number"},
        ),
        "cartAddData_totalTwoDayShippingCartAddCount": (
            "totalTwoDayShippingCartAddCount",
            {"type": "number"},
        ),
        "purchaseData_totalPurchaseCount": ("totalPurchaseCount", {"type": "number"}),
        "purchaseData_totalPurchaseRate": ("totalPurchaseRate", {"type": "percent"}),
        "purchaseData_asinPurchaseCount": ("asinPurchaseCount", {"type": "number"}),
        "purchaseData_asinPurchaseShare": ("asinPurchaseShare", {"type": "percent"}),
        "totalMedianPurchasePrice_amount": (
            "totalMedianPurchasePrice_amount",
            {"type": "currency"},
        ),
        "totalMedianPurchasePrice_currencyCode": (
            "totalMedianPurchasePrice_currencyCode",
            {"type": ""},
        ),
        "asinMedianPurchasePrice_amount": (
            "asinMedianPurchasePrice_amount",
            {"type": "currency"},
        ),
        "asinMedianPurchasePrice_currencyCode": (
            "asinMedianPurchasePrice_currencyCode",
            {"type": ""},
        ),
        "purchaseData_totalSameDayShippingPurchaseCount": (
            "totalSameDayShippingPurchaseCount",
            {"type": "number"},
        ),
        "purchaseData_totalOneDayShippingPurchaseCount": (
            "totalOneDayShippingPurchaseCount",
            {"type": "number"},
        ),
        "purchaseData_totalTwoDayShippingPurchaseCount": (
            "totalTwoDayShippingPurchaseCount",
            {"type": "number"},
        ),
        "cartAddData_asinMedianCartAddPrice": ("asinMedianCartAddPrice", {"type": ""}),
        "purchaseData_asinMedianPurchasePrice": (
            "asinMedianPurchasePrice",
            {"type": "currency"},
        ),
        "clickData_asinMedianClickPrice": ("asinMedianClickPrice", {"type": ""}),
        "cartAddData_totalMedianCartAddPrice": (
            "totalMedianCartAddPrice",
            {"type": "currency"},
        ),
        "purchaseData_totalMedianPurchasePrice": (
            "totalMedianPurchasePrice",
            {"type": "currency"},
        ),
        "clickData_totalMedianClickPrice": (
            "totalMedianClickPrice",
            {"type": "currency"},
        ),
        "period": ("period", {"type": ""}),
        "marketplaces": ("marketplaces", {"type": ""}),
    }

    if not sqp_raw.columns.tolist() == list(target_cols.keys()):
        wrong_cols = [
            x for x in sqp_raw.columns.tolist() if x not in list(target_cols.keys())
        ] or [x for x in list(target_cols.keys()) if x not in sqp_raw.columns.tolist()]
        return {"status": "error", "message": ", ".join(wrong_cols)}

    blank_cols = [
        "asinMedianCartAddPrice",
        "asinMedianPurchasePrice",
        "asinMedianClickPrice",
        "totalMedianCartAddPrice",
        "totalMedianPurchasePrice",
        "totalMedianClickPrice",
    ]

    return {
        "status": "success",
        "target_cols": target_cols,
        "blank_cols": blank_cols,
    }


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


def calculate_weighted_prices(
    df: pd.DataFrame, index_cols: list, sum_cols: list, price_cols: list
) -> pd.DataFrame:

    df[sum_cols + price_cols] = df[sum_cols + price_cols].astype(float).fillna(0)

    impression_cols = [x for x in sum_cols if "Impression" in x]
    shipping_cols = [x for x in sum_cols if "Shipping" in x]

    sum_cols_asin = [
        x
        for x in sum_cols
        if (x not in impression_cols + shipping_cols and x.startswith("asin"))
    ]
    sum_cols_total = [
        x
        for x in sum_cols
        if (x not in impression_cols + shipping_cols and x.startswith("total"))
    ]

    price_cols_asin = [x for x in price_cols if x.startswith("asin")]
    price_cols_total = [x for x in price_cols if x.startswith("total")]

    click_pair_asin = [x for x in (sum_cols_asin + price_cols_asin) if "Click" in x]
    atc_pair_asin = [x for x in (sum_cols_asin + price_cols_asin) if "Cart" in x]
    purchase_pair_asin = [
        x for x in (sum_cols_asin + price_cols_asin) if "Purchase" in x
    ]

    click_pair_total = [x for x in (sum_cols_total + price_cols_total) if "Click" in x]
    atc_pair_total = [x for x in (sum_cols_total + price_cols_total) if "Cart" in x]
    purchase_pair_total = [
        x for x in (sum_cols_total + price_cols_total) if "Purchase" in x
    ]

    df["click_product_asin"] = df[click_pair_asin[0]] * df[click_pair_asin[1]]
    df["atc_product_asin"] = df[atc_pair_asin[0]] * df[atc_pair_asin[1]]
    df["purchase_product_asin"] = df[purchase_pair_asin[0]] * df[purchase_pair_asin[1]]

    group_cols = sum_cols + [
        "click_product_asin",
        "atc_product_asin",
        "purchase_product_asin",
    ]
    if click_pair_total:
        df["click_product_total"] = df[click_pair_total[0]] * df[click_pair_total[1]]
        df["atc_product_total"] = df[atc_pair_total[0]] * df[atc_pair_total[1]]
        df["purchase_product_total"] = (
            df[purchase_pair_total[0]] * df[purchase_pair_total[1]]
        )
        group_cols += [
            "click_product_total",
            "atc_product_total",
            "purchase_product_total",
        ]

    summary = df.groupby(index_cols)[group_cols].agg("sum").reset_index()

    summary[click_pair_asin[1]] = (
        summary["click_product_asin"] / summary[click_pair_asin[0]]
    )
    summary[atc_pair_asin[1]] = summary["atc_product_asin"] / summary[atc_pair_asin[0]]
    summary[purchase_pair_asin[1]] = (
        summary["purchase_product_asin"] / summary[purchase_pair_asin[0]]
    )

    if click_pair_total:
        summary[click_pair_total[1]] = (
            summary["click_product_total"] / summary[click_pair_total[0]]
        )
        summary[atc_pair_total[1]] = (
            summary["atc_product_total"] / summary[atc_pair_total[0]]
        )
        summary[purchase_pair_total[1]] = (
            summary["purchase_product_total"] / summary[purchase_pair_total[0]]
        )

    return summary.loc[:, index_cols + price_cols]


def group_by_index(
    df: pd.DataFrame,
    index_cols: list,
    immutable_cols: list,
    sum_cols: list,
    price_cols: list,
) -> pd.DataFrame:
    if len(immutable_cols) == 0:
        totals_df = pd.DataFrame(columns=pd.Index(index_cols))
    else:
        totals_df = df.groupby(index_cols)[immutable_cols].agg("min").reset_index()
    sums_df = df.groupby(index_cols)[sum_cols].agg("sum").reset_index()
    price_df = calculate_weighted_prices(
        df=df.copy(), index_cols=index_cols, sum_cols=sum_cols, price_cols=price_cols
    )
    result = pd.merge(totals_df, sums_df, how="outer", on=index_cols, validate="1:1")
    result = pd.merge(result, price_df, how="outer", on=index_cols, validate="1:1")

    return result


def add_missing_columns(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df["ASINs shown"] = df["totalQueryImpressionCount"] / df["searchQueryVolume"]
        df["asinImpressionShare"] = (
            df["asinImpressionCount"] / df["totalQueryImpressionCount"]
        )
        df["asinClickShare"] = df["asinClickCount"] / df["totalClickCount"]
        df["asinCTR"] = df["asinClickCount"] / df["asinImpressionCount"]
        df["asinCartAddShare"] = df["asinCartAddCount"] / df["totalCartAddCount"]
        df["asinClickToAtcConversion"] = df["asinCartAddCount"] / df["asinClickCount"]
        df["asinPurchaseShare"] = df["asinPurchaseCount"] / df["totalPurchaseCount"]
        df["asinConversion"] = df["asinPurchaseCount"] / df["asinClickCount"]
        df["totalClickRate"] = df["totalClickCount"] / df["searchQueryVolume"]
        df["totalCartAddRate"] = df["totalCartAddCount"] / df["searchQueryVolume"]
        df["totalPurchaseRate"] = df["totalPurchaseCount"] / df["searchQueryVolume"]
    except Exception as e:
        raise BaseException(f"Could not add missing columns: {e}")

    return df


def reorder_df(
    df: pd.DataFrame,
    original_cols: list,
    blank_cols: list,
    target: Literal["query_date", "query", "date", "full"],
) -> pd.DataFrame:
    ordered_cols = [
        x
        for x in original_cols
        if not ("currency" in x or "Score" in x or x in blank_cols)
    ]
    match target:
        case "query_date":
            _ = ordered_cols.pop(ordered_cols.index("asin"))
        case "query":
            ordered_cols = [x for x in ordered_cols if "Date" not in x]
        case "date":
            ordered_cols = [
                x for x in ordered_cols if not (x == "asin" or x == "searchQuery")
            ]
    total_click_count_index = ordered_cols.index("totalClickRate")
    ordered_cols.insert(total_click_count_index, "ASINs shown")

    asin_click_share_index = ordered_cols.index("asinClickShare")
    ordered_cols.insert(asin_click_share_index, "asinCTR")

    asin_purchase_share_index = ordered_cols.index("asinPurchaseShare")
    ordered_cols.insert(asin_purchase_share_index, "asinConversion")

    return df.loc[:, ordered_cols]


def calculate_sqp(sqp_raw: pd.DataFrame):
    column_check = check_sqp_columns(sqp_raw)
    if column_check.get("status") == "error":
        raise BaseException(f"Columns do not match: {column_check.get('message')}")
    target_cols_dict, blank_cols = (
        column_check.get("target_cols", []),
        column_check.get("blank_cols", []),
    )

    target_cols = {key: value[0] for key, value in target_cols_dict.items()}
    column_formatting = {x[0]: x[1] for x in target_cols_dict.values() if x[1]["type"]}
    column_formatting.update(
        {
            "ASINs shown": {"type": "number", "decimal": 1},
            "asinCTR": {"type": "percent", "precision": 2},
        }
    )

    sqp = sqp_raw.rename(columns=target_cols)

    sqp_asin = add_missing_columns(sqp.copy())
    sqp_asin = reorder_df(
        df=sqp_asin.copy(),
        original_cols=list(target_cols.values()),
        blank_cols=blank_cols,
        target="full",
    )

    # calculate results by date and search query
    immutable_cols = [x for x in target_cols.values() if x.startswith("total")] + [
        "searchQueryVolume"
    ]

    sum_cols = [
        x
        for x in target_cols.values()
        if (x.startswith("asin") and x.endswith("Count"))
    ]
    price_cols = [
        x
        for x in target_cols.values()
        if (x.startswith("asin") and x.endswith("Price_amount"))
    ]

    date_query_report = group_by_index(
        sqp.copy(),
        index_cols=[
            "startDate",
            "endDate",
            "searchQuery",
            "period",
            "marketplaces",
        ],
        immutable_cols=immutable_cols,
        sum_cols=sum_cols,
        price_cols=price_cols,
    )
    date_query_report = add_missing_columns(df=date_query_report.copy())
    date_query_report = reorder_df(
        date_query_report,
        original_cols=list(target_cols.values()),
        blank_cols=blank_cols,
        target="query_date",
    )

    # calculate results by DATE ONLY
    immutable_cols = []

    sum_cols = [
        x
        for x in target_cols.values()
        if ((x.startswith("asin") or x.startswith("total")) and x.endswith("Count"))
    ] + ["searchQueryVolume"]
    price_cols = [
        x
        for x in target_cols.values()
        if (
            (x.startswith("asin") or x.startswith("total"))
            and x.endswith("Price_amount")
        )
    ]

    date_report = group_by_index(
        date_query_report.copy(),
        index_cols=[
            "startDate",
            "endDate",
            "period",
            "marketplaces",
        ],
        sum_cols=sum_cols,
        immutable_cols=immutable_cols,
        price_cols=price_cols,
    )
    date_report = add_missing_columns(date_report.copy())
    date_report = reorder_df(
        date_report,
        original_cols=list(target_cols.values()),
        blank_cols=blank_cols,
        target="date",
    )
    return sqp_asin, date_query_report, date_report, column_formatting


def main():
    sqp_raw_result = pull_sqp_asin_data(asins, start_date)
    if not sqp_raw_result.get("status") == "success":
        raise BaseException(f"Could not pull SQP data: {sqp_raw_result.get('message')}")
    sqp_raw = sqp_raw_result["result"]
    if not isinstance(sqp_raw, pd.DataFrame):
        raise BaseException("sqp_raw is not a vaild dataframe")

    sqp_asin, date_query_report, date_report, column_formatting = calculate_sqp(
        sqp_raw=sqp_raw
    )
    _ = export_to_excel(
        dfs=[sqp_asin, date_query_report, date_report],
        sheet_names=["ASIN", "Search Query", "Date"],
        filename="SQP report.xlsx",
        out_folder=user_folder,
        column_formats=column_formatting,
    )


if __name__ == "__main__":
    main()
