import populate_env  # isort: skip
import asyncio
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from scheduled.sqp_reports import run_sqp_reports
from streamlit_echarts import st_echarts

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
filter_kw_col, clear_btn_col, start_date_col, end_date_col, run_btn_col = dates_container.columns(
    [3, 1, 2, 2, 1]
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

_ = pull_dictionary()  # pre-populate dictionary
filtered_dictionary = filter_dictionary(
    coll_target=coll_col,
    size_target=size_col,
    color_target=color_col,
    clear_btn_target=clear_btn_col,
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
        if not failed_reports or failed_reports == "":
            return
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
        if sqp_raw is None:
            st.warning(
                "Sorry, Amazon reports take longer to generate than expected, try later"
            )
        else:
            st.session_state.sqp, st.session_state.check_columns = check_sqp(
                sqp_raw=sqp_raw
            )

    except Exception as e:
        st.error(e)


run_btn_col.button(
    "Run",
    on_click=run_sqp_analysis,
    args=(start_date, end_date),
    type="primary",
    use_container_width=True,
)


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
        import json as _json

        from modules.sqp_analytics import (
            HELP,
            asin_sankey_chart,
            build_sqp_report,
            cart_abandonment_chart,
            funnel_chart,
            funnel_leakage_heatmap,
            keyword_momentum_chart,
            missed_opportunity_chart,
            price_position_chart,
            share_of_voice_chart,
            strategy_matrix,
        )

        slider_col, export_col = st.columns([3, 1])

        with slider_col:
            top_n = st.slider(
                "Keywords to show per chart",
                min_value=5, max_value=100, value=15, step=5,
                help="Controls how many keywords appear in each chart (sorted by relevance to that chart)",
            )

        with export_col:
            st.write("")  # spacer to align with slider
            report_payload = build_sqp_report(
                combined_report=st.session_state.combined_report,
                query_report=st.session_state.query_report,
                date_report=st.session_state.date_report,
                date_query_report=st.session_state.date_query_report,
                asins=list(pd.unique(filtered_dictionary["asin"])) if not filtered_dictionary.empty else [],
                filters={
                    "keyword_search": st.session_state.get("filter_search", ""),
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                },
                top_n=top_n,
            )
            st.download_button(
                label=":material/download: Export for AI analysis",
                data=_json.dumps(report_payload, indent=2, default=str),
                file_name=f"sqp_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                help="Downloads a structured JSON report with all metrics and pre-computed insights, ready to send to an AI agent for analysis",
            )

        # Row 1: Conversion Funnel + Radar
        row1_left, row1_right = st.columns(2)
        with row1_left:
            st.subheader("Conversion Funnel")
            with st.expander("What does this mean?", icon=":material/help:"):
                st.markdown(HELP["funnel"])
            opts = funnel_chart(st.session_state.combined_report)
            if opts:
                st_echarts(options=opts, height="400px")

        with row1_right:
            st.subheader("ASIN vs Niche")
            radar_data_df = st.session_state.combined_report.copy()
            radar_options = radar_charts(df=radar_data_df)
            if radar_options:
                st_echarts(options=radar_options)

        # ASIN Sankey flow (full width, under funnel row)
        st.subheader("ASIN Customer Journey")
        with st.expander("What does this mean?", icon=":material/help:"):
            st.markdown(HELP["sankey"])
        show_dropoffs = st.checkbox(
            "Show drop-offs",
            value=True,
            help="Toggle to hide the red drop-off branches and see only the continuing flow",
        )
        sankey_opts = asin_sankey_chart(
            st.session_state.combined_report, show_dropoffs=show_dropoffs
        )
        if sankey_opts:
            st_echarts(options=sankey_opts, height="500px")

        st.divider()

        # Row 2: Strategy Matrix (full width)
        st.subheader("Keyword Strategy Matrix")
        with st.expander("What does this mean?", icon=":material/help:"):
            st.markdown(HELP["strategy_matrix"])
        opts = strategy_matrix(st.session_state.query_report)
        if opts:
            st_echarts(options=opts, height="500px")

        st.divider()

        # Row 3: Missed Opportunity + Price Position
        row3_left, row3_right = st.columns(2)
        with row3_left:
            st.subheader("Missed Opportunities")
            with st.expander("What does this mean?", icon=":material/help:"):
                st.markdown(HELP["missed_opportunity"])
            opts = missed_opportunity_chart(st.session_state.query_report, top_n=top_n)
            if opts:
                st_echarts(options=opts, height="450px")

        with row3_right:
            st.subheader("Competitive Price Position")
            with st.expander("What does this mean?", icon=":material/help:"):
                st.markdown(HELP["price_position"])
            opts = price_position_chart(st.session_state.query_report)
            if opts:
                st_echarts(options=opts, height="450px")

        st.divider()

        # Row 4: Funnel Leakage Heatmap (full width)
        st.subheader("Funnel Leakage by Keyword")
        with st.expander("What does this mean?", icon=":material/help:"):
            st.markdown(HELP["leakage_heatmap"])
        opts = funnel_leakage_heatmap(st.session_state.query_report, top_n=top_n)
        if opts:
            st_echarts(options=opts, height="500px")

        st.divider()

        # Row 5: Share of Voice + Keyword Momentum (multi-week only)
        row5_left, row5_right = st.columns(2)
        with row5_left:
            st.subheader("Share of Voice Over Time")
            with st.expander("What does this mean?", icon=":material/help:"):
                st.markdown(HELP["share_of_voice"])
            opts = share_of_voice_chart(st.session_state.date_report)
            if opts:
                st_echarts(options=opts, height="400px")
            else:
                st.info("Select multiple weeks to see trends.")

        with row5_right:
            st.subheader("Keyword Momentum")
            with st.expander("What does this mean?", icon=":material/help:"):
                st.markdown(HELP["keyword_momentum"])
            opts = keyword_momentum_chart(st.session_state.date_query_report, top_n=top_n)
            if opts:
                st_echarts(options=opts, height="400px")
            else:
                st.info("Select multiple weeks to see momentum.")

        st.divider()

        # Row 6: Cart Abandonment
        st.subheader("Cart Abandonment vs Market")
        with st.expander("What does this mean?", icon=":material/help:"):
            st.markdown(HELP["cart_abandonment"])
        opts = cart_abandonment_chart(st.session_state.query_report, top_n=top_n)
        if opts:
            st_echarts(options=opts, height="450px")

        st.divider()

        # Row 7: Parallel Coordinates (existing, moved to bottom)
        st.subheader("Parallel Coordinates")
        with st.expander("What does this mean?", icon=":material/help:"):
            st.markdown(HELP["parallel_coordinates"])
        parallels_data_df = st.session_state.query_report.copy()
        parallel_options = parallel_coordinates_charts(df=parallels_data_df)
        if parallel_options:
            st_echarts(options=parallel_options, height="600px")
