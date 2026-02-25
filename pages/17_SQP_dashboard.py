import asyncio
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from login import require_login
from modules.filter_modules import filter_dictionary
from modules.gcloud_modules import pull_dictionary
from modules.sp_api_modules import run_sqp_reports
from modules.sqp_modules import calculate_sqp, pull_sqp_asin_data

st.set_page_config(
    page_title="SQP analyzer",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)


require_login()

user_email = st.user.email

filter_col, start_date_col, end_date_col = st.columns([4, 1, 1])
start_date_text_input, start_date_date_input = start_date_col.columns([1, 2])
end_date_text_input, end_date_date_input = end_date_col.columns([1, 2])

start_date_text_input.write("Start:")
start_date = start_date_date_input.date_input(
    label="Start date", label_visibility="collapsed"
)

end_date_text_input.write("End:")
end_date = end_date_date_input.date_input(
    label="End date",
    label_visibility="collapsed",
    max_value=datetime.now() - timedelta(days=8),
)


asyncio.run(pull_dictionary())  # pre-populate dictionary
filtered_dictionary = asyncio.run(filter_dictionary(col=filter_col))


def filter_sundays(start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date)
    return [str(x.date()) for x in date_range if x.weekday() == 6]


async def get_sqp_data(start_date=start_date, end_date=end_date):
    asins = list(pd.unique(filtered_dictionary["asin"]))
    if len(asins) > 100:
        raise BaseException(
            f"Please don't submit more than 100 ASINs at a time. You are currently trying to pull {len(asins)} asins"
        )
    dates = filter_sundays(start_date=start_date, end_date=end_date)
    sqp_raw_result = pull_sqp_asin_data(asins, dates)

    if not sqp_raw_result.get("status") == "success":
        raise BaseException(f"Could not pull SQP data: {sqp_raw_result.get('message')}")
    sqp_raw = sqp_raw_result["result"]
    if not isinstance(sqp_raw, pd.DataFrame):
        raise BaseException("sqp_raw is not a vaild dataframe")

    current_asins = {
        (start_date, asin)
        for start_date, asin in sqp_raw[["startDate", "asin"]].drop_duplicates().values
    }
    missing_asins = {}
    for date in dates:
        missing_asins[date] = []
        for asin in asins:
            if (date, asin) not in current_asins:
                missing_asins[date].append(asin)

    if any(len(missing_asins[x]) > 0 for x in missing_asins):
        missing_str = {date: len(missing_asins[date]) for date in missing_asins}
        missing_str_text = "Missing: " + "\n".join(
            [f"{key}: {value} asins" for key, value in missing_str.items() if value > 0]
        )
        st.toast(missing_str_text)
        st.info("Pulling information from Amazon reports, this could take a while")
        date_asin_dict = {d: v for d, v in missing_asins.items() if len(v) > 0}
        await run_sqp_reports(date_asin_dict=date_asin_dict)
        sqp_asin, date_query_report, date_report, column_formatting = (
            await get_sqp_data(start_date=start_date, end_date=end_date)
        )

    sqp_asin, date_query_report, date_report, column_formatting = calculate_sqp(
        sqp_raw=sqp_raw
    )
    return sqp_asin, date_query_report, date_report, column_formatting


def get_column_config(column_formatting):
    column_formats = {}
    for col in column_formatting:
        col_name = col
        col_format = column_formatting[col]["type"]
        match col_format:
            case "number":
                column_formats[col_name] = st.column_config.NumberColumn(
                    format="localized"
                )
            case "percent":
                column_formats[col_name] = st.column_config.NumberColumn(
                    format="percent"
                )
            case "currency":
                column_formats[col_name] = st.column_config.NumberColumn(
                    format="dollar"
                )
    return column_formats


def run_sqp_analysis(start_date, end_date):
    try:
        sqp_asin, date_query_report, date_report, column_formatting = asyncio.run(
            get_sqp_data(start_date, end_date)
        )
        st.dataframe(date_report, column_config=get_column_config(column_formatting))
        st.dataframe(
            date_query_report, column_config=get_column_config(column_formatting)
        )

    except Exception as e:
        st.error(e)


st.button("Run", on_click=run_sqp_analysis, args=(start_date, end_date))
