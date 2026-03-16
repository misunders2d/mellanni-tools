import asyncio
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from scheduled.sqp_reports import run_sqp_reports
from streamlit_echarts import st_echarts

import login
from login import require_login
from modules.filter_modules import filter_column, filter_dictionary
from modules.gcloud_modules import pull_dictionary
from modules.sqp_charts import parallel_coordinates_charts, radar_charts
from modules.sqp_modules import calculate_sqp, check_sqp, pull_sqp_asin_data

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
dashboard_container = st.container()
dashboard_tab, excel_tab = st.tabs(["Dashboard", "Excel"])
dfs_container = excel_tab.container()
coll_col, size_col, color_col = filter_container.columns([4, 2, 2])
filter_kw_col, clear_btn_col, start_date_col, end_date_col = dates_container.columns(
    [3, 1, 2, 2]
)

end_date = end_date_col.date_input(
    label="End date",
    label_visibility="collapsed",
    max_value=datetime.now() - timedelta(days=8),
)
start_date = start_date_col.date_input(
    label="Start date", label_visibility="collapsed", max_value=end_date
)


def run_df_filter():
    st.session_state.filter_search = st.session_state.phrase
    if st.session_state.filter_search == "" or not st.session_state.filter_search:
        st.session_state.sqp_filtered = st.session_state.sqp.copy()
    else:
        # st.write(st.session_state.sqp_raw)
        st.session_state.sqp_filtered = filter_column(
            df=st.session_state.sqp.copy(),
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


async def get_sqp_data(
    start_date=start_date, end_date=end_date, failed_asins: list | None = None
):
    asins = list(pd.unique(filtered_dictionary["asin"]))
    if (
        failed_asins
    ):  # means some of the asins were already requested from Amazon and the reports failed.
        failed_asins_dict = {
            date_str.split("T")[0]: asin_str.split()
            for date_str, asin_str in failed_asins
        }
        failed_asins_list = [
            asin for sublist in failed_asins_dict.values() for asin in sublist
        ]
        asins = [
            x for x in asins if x not in failed_asins_list
        ]  # removing failed asins from the requested asins list

    if len(asins) > 100:
        st.warning(
            f"Please don't submit more than 100 ASINs at a time. You are currently trying to pull {len(asins)} asins"
        )

        raise BaseException(
            f"Please don't submit more than 100 ASINs at a time. You are currently trying to pull {len(asins)} asins"
        )
        st.stop()
    elif len(asins) == 0:
        st.warning(
            "All ASINs are currently unreportable for this timeframe, please wait for a few hours or select a date that is one week earlier"
        )
        st.stop()
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
    # checking if some of the requested asins did not return from bigquery table. in this case we're requesting them from Amazon directly.
    for date in dates:
        missing_asins[date] = []
        for asin in asins:
            if (date, asin) not in current_asins:
                missing_asins[date].append(asin)
    if failed_asins:
        failed_asins_dict = {
            date_str.split("T")[0]: asin_str.split()
            for date_str, asin_str in failed_asins
        }
        st.toast(
            f"Please note, the following reports failed, they are not ready in Amazon yet: {str(failed_asins)}"
        )
        for date, asin_list in failed_asins_dict.items():
            for asin in asin_list:
                pass
                if asin in failed_asins_dict[date]:
                    missing_asins[date].remove(asin)

    if any(len(missing_asins[x]) > 0 for x in missing_asins):
        missing_str = {date: len(missing_asins[date]) for date in missing_asins}
        missing_str_text = "Missing: " + "\n".join(
            [f"{key}: {value} asins" for key, value in missing_str.items() if value > 0]
        )
        st.toast(missing_str_text)
        st.info("Pulling information from Amazon reports, this could take a while")
        date_asin_dict = {d: v for d, v in missing_asins.items() if len(v) > 0}
        failed_reports = await run_sqp_reports(date_asin_dict=date_asin_dict)
        sqp_raw = await get_sqp_data(
            start_date=start_date, end_date=end_date, failed_asins=failed_reports
        )

    return sqp_raw


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
    if "sqp" in st.session_state:
        del st.session_state.sqp
    if "sqp_filtered" in st.session_state:
        del st.session_state.sqp_filtered

    try:
        sqp_raw = asyncio.run(get_sqp_data(start_date, end_date))
        st.session_state.sqp, st.session_state.check_columns = check_sqp(
            sqp_raw=sqp_raw
        )

    except Exception as e:
        st.error(e)


st.button("Run", on_click=run_sqp_analysis, args=(start_date, end_date))

if "sqp" in st.session_state:
    sqp_to_process = (
        st.session_state.sqp_filtered
        if "sqp_filtered" in st.session_state
        else st.session_state.sqp
    )

    with excel_tab:
        reports = calculate_sqp(
            sqp=sqp_to_process,
            check_columns=st.session_state.check_columns,
        )
        st.session_state.combined_report = reports["combined_report"]
        st.session_state.date_report = reports["date_report"]
        st.session_state.query_report = reports["query_report"]
        st.session_state.date_query_report = reports["date_query_report"]
        st.session_state.sqp_asin = reports["sqp_asin"]

        # render combined df
        dfs_container.dataframe(
            st.session_state.combined_report,
            column_config=get_column_config(
                st.session_state.check_columns["column_formatting"]
            ),
            hide_index=True,
        )

        # render date df
        dfs_container.dataframe(
            st.session_state.date_report,
            column_config=get_column_config(
                st.session_state.check_columns["column_formatting"]
            ),
            hide_index=True,
        )

        # render query df
        dfs_container.dataframe(
            st.session_state.query_report,
            column_config=get_column_config(
                st.session_state.check_columns["column_formatting"]
            ),
            hide_index=True,
        )

        # render date_query df
        dfs_container.dataframe(
            data=st.session_state.date_query_report,
            column_config=get_column_config(
                st.session_state.check_columns["column_formatting"]
            ),
            hide_index=True,
        )

        # render sqp_asin df
        dfs_container.dataframe(
            data=st.session_state.sqp_asin,
            column_config=get_column_config(
                st.session_state.check_columns["column_formatting"]
            ),
            hide_index=True,
        )

    with dashboard_tab:
        parallels_data_df = st.session_state.query_report.copy()
        parallel_options = parallel_coordinates_charts(df=parallels_data_df)
        if parallel_options:
            st_echarts(options=parallel_options, height="600px")
        radar_data_df = st.session_state.combined_report.copy()
        radar_options = radar_charts(df=radar_data_df)
        if radar_options:
            st_echarts(options=radar_options)

        # data_df = st.session_state.date_query_report.copy()
        # x_axis = {"type": "time", "name": "Date"}
        # y_axis = {"type": "value", "name": "Price ($)"}
        #
        # dates = data_df["startDate"].tolist()
        # searches = data_df["searchQueryVolume"].tolist()
        #
        # total_click_prices = data_df["totalMedianClickPrice_amount"].tolist()
        # total_atc_prices = data_df["totalMedianCartAddPrice_amount"].tolist()
        # total_purchase_prices = data_df["totalMedianPurchasePrice_amount"].tolist()
        #
        # total_click_data = list(zip(dates, total_click_prices, searches))
        # total_atc_data = list(zip(dates, total_atc_prices, searches))
        # total_purchase_data = list(zip(dates, total_purchase_prices, searches))
        #
        # series = [
        #     {
        #         "name": "Click Price",
        #         "type": "scatter",
        #         "data": total_click_data,
        #         "itemStyle": {"color": "#5470c6", "opacity": 0.5},  # Blue
        #     },
        #     {
        #         "name": "ATC Price",
        #         "type": "scatter",
        #         "data": total_atc_data,
        #         "itemStyle": {"color": "#91cc75", "opacity": 0.5},  # Green
        #     },
        #     {
        #         "name": "Purchase Price",
        #         "type": "scatter",
        #         "data": total_purchase_data,
        #         "itemStyle": {"color": "#fac858", "opacity": 0.5},  # Yellow/Orange
        #     },
        # ]
        # scatter_options = scatter_charts(x_axis=x_axis, y_axis=y_axis, series=series)
        # st_echarts(options=scatter_options)
