import asyncio
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from login import require_login
from modules.filter_modules import filter_column, filter_dictionary
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

filter_container = st.container()
dates_container = st.container()
dfs_container = st.container()
coll_col, size_col, color_col = filter_container.columns([4, 2, 2])
filter_kw_col, clear_btn_col, start_date_col, end_date_col = dates_container.columns(
    [3, 1, 2, 2]
)

start_date = start_date_col.date_input(label="Start date", label_visibility="collapsed")
end_date = end_date_col.date_input(
    label="End date",
    label_visibility="collapsed",
    max_value=datetime.now() - timedelta(days=8),
)


def run_df_filter():
    st.session_state.filter_search = st.session_state.phrase
    if st.session_state.filter_search == "" or not st.session_state.filter_search:
        st.session_state.sqp_asin_filtered = st.session_state.sqp_asin.copy()
        st.session_state.date_query_report_filtered = (
            st.session_state.date_query_report.copy()
        )
    else:
        st.session_state.sqp_asin_filtered = filter_column(
            df=st.session_state.sqp_asin.copy(),
            col="searchQuery",
            target=st.session_state.filter_search,
        )

        st.session_state.date_query_report_filtered = filter_column(
            df=st.session_state.date_query_report.copy(),
            col="searchQuery",
            target=st.session_state.filter_search,
        )


filter_kw = filter_kw_col.text_input(
    label="Filter keywords",
    placeholder="Enter keywords to search",
    label_visibility="collapsed",
    on_change=run_df_filter,
    key="phrase",
)

asyncio.run(pull_dictionary())  # pre-populate dictionary
filtered_dictionary = asyncio.run(
    filter_dictionary(
        coll_target=coll_col,
        size_target=size_col,
        color_target=color_col,
        clear_btn_target=clear_btn_col,
    )
)


def filter_sundays(start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date)
    return [str(x.date()) for x in date_range if x.weekday() == 6]


async def get_sqp_data(start_date=start_date, end_date=end_date):
    asins = list(pd.unique(filtered_dictionary["asin"]))
    if len(asins) > 100:
        st.warning(
            f"Please don't submit more than 100 ASINs at a time. You are currently trying to pull {len(asins)} asins"
        )

        st.stop()
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
        (
            st.session_state.sqp_asin,
            st.session_state.date_query_report,
            st.session_state.date_report,
            st.session_state.column_formatting,
        ) = asyncio.run(get_sqp_data(start_date, end_date))

    except Exception as e:
        st.error(e)


st.button("Run", on_click=run_sqp_analysis, args=(start_date, end_date))

if "date_report" in st.session_state:
    dfs_container.dataframe(
        st.session_state.date_report,
        column_config=get_column_config(st.session_state.column_formatting),
        hide_index=True,
    )

if "date_query_report" in st.session_state:
    dfs_container.dataframe(
        data=(
            st.session_state.date_query_report_filtered
            if "date_query_report_filtered" in st.session_state
            else st.session_state.date_query_report
        ),
        column_config=get_column_config(st.session_state.column_formatting),
        hide_index=True,
    )

if "sqp_asin" in st.session_state:
    dfs_container.dataframe(
        data=(
            st.session_state.sqp_asin_filtered
            if "sqp_asin_filtered" in st.session_state
            else st.session_state.sqp_asin
        ),
        column_config=get_column_config(st.session_state.column_formatting),
        hide_index=True,
    )
