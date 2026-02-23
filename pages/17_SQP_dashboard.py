import asyncio

import pandas as pd
import streamlit as st

from login import require_login
from modules.filter_modules import filter_dictionary
from modules.gcloud_modules import pull_dictionary
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
    label="End date", label_visibility="collapsed"
)


asyncio.run(pull_dictionary())  # pre-populate dictionary
filtered_dictionary = asyncio.run(filter_dictionary(col=filter_col))


def filter_sundays(start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date)
    return [str(x.date()) for x in date_range if x.weekday() == 6]


def get_sqp_data():
    asins = list(pd.unique(filtered_dictionary["asin"]))
    dates = filter_sundays(start_date=start_date, end_date=end_date)

    sqp_raw_result = pull_sqp_asin_data(asins, dates)
    if not sqp_raw_result.get("status") == "success":
        raise BaseException(f"Could not pull SQP data: {sqp_raw_result.get('message')}")
    sqp_raw = sqp_raw_result["result"]
    if not isinstance(sqp_raw, pd.DataFrame):
        raise BaseException("sqp_raw is not a vaild dataframe")

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


if st.button("Run"):
    sqp_asin, date_query_report, date_report, column_formatting = get_sqp_data()

    st.dataframe(date_report, column_config=get_column_config(column_formatting))
