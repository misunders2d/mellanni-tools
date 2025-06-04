import streamlit as st
import pandas as pd
import pandas_gbq
from fuzzywuzzy import fuzz
import os, re, time
from typing import Literal, Dict
from modules import gcloud_modules as gc
from modules import formatting as ff
from plotly.subplots import make_subplots
import plotly.graph_objects as go

st.set_page_config(page_title = 'SQP analyzer', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')

from login import login_st
if login_st():
    user_email = st.user.email

    kw_filter_area, slider_area, button_area = st.columns([3,7,2], vertical_alignment='center', gap='medium')
    sqp_tab, kw_tab = st.tabs(['SQP results', 'Keywords stats'])
    kw_plot_area = kw_tab.empty()
    kw_df1, kw_df2 = kw_tab.columns([1,1], gap='small')

    ### SQP tab -------------------------------------------------------------------

    numeric_cols=['Search Query Volume','Impressions: Total Count','Clicks: Total Count','Cart Adds: Total Count','Purchases: Total Count',
                            'Impressions: Brand Count','Clicks: Brand Count','Cart Adds: Brand Count','Purchases: Brand Count','ASINs shown'],
    currency_cols=['Clicks: Price (Median)','Cart Adds: Price (Median)','Purchases: Price (Median)','Clicks: Brand Price (Median)',
                    'Cart Adds: Brand Price (Median)','Purchases: Brand Price (Median)'],
    percent_cols=['ASINs glance rate','KW ctr','ASIN ctr','KW ATC %','ASINs ATC %','KW ATC conversion','ASINs ATC conversion',
                            'KW conversion','ASINs conversion']

    renaming = {'search_query': 'Search Query',
                'search_query_volume': 'Search Query Volume',
                'impressions:_total_count': 'Impressions: Total Count',
                'impressions:_brand_count': 'Impressions: Brand Count',
                'impressions:_brand_share_%': 'Impressions: Brand Share %',
                'clicks:_total_count': 'Clicks: Total Count',
                'clicks:_click_rate_%': 'Clicks: Click Rate %',
                'clicks:_brand_count': 'Clicks: Brand Count',
                'clicks:_brand_share_%': 'Clicks: Brand Share %',
                'clicks:_price_median': 'Clicks: Price (Median)',
                'clicks:_brand_price_median': 'Clicks: Brand Price (Median)',
                'clicks:_same_day_shipping_speed': 'Clicks: Same Day Shipping Speed',
                'clicks:_1d_shipping_speed': 'Clicks: 1D Shipping Speed',
                'clicks:_2d_shipping_speed': 'Clicks: 2D Shipping Speed',
                'cart_adds:_total_count': 'Cart Adds: Total Count',
                'cart_adds:_cart_add_rate_%': 'Cart Adds: Cart Add Rate %',
                'cart_adds:_brand_count': 'Cart Adds: Brand Count',
                'cart_adds:_brand_share_%': 'Cart Adds: Brand Share %',
                'cart_adds:_price_median': 'Cart Adds: Price (Median)',
                'cart_adds:_brand_price_median': 'Cart Adds: Brand Price (Median)',
                'cart_adds:_same_day_shipping_speed': 'Cart Adds: Same Day Shipping Speed',
                'cart_adds:_1d_shipping_speed': 'Cart Adds: 1D Shipping Speed',
                'cart_adds:_2d_shipping_speed': 'Cart Adds: 2D Shipping Speed',
                'purchases:_total_count': 'Purchases: Total Count',
                'purchases:_purchase_rate_%': 'Purchases: Purchase Rate %',
                'purchases:_brand_count': 'Purchases: Brand Count',
                'purchases:_brand_share_%': 'Purchases: Brand Share %',
                'purchases:_price_median': 'Purchases: Price (Median)',
                'purchases:_brand_price_median': 'Purchases: Brand Price (Median)',
                'purchases:_same_day_shipping_speed': 'Purchases: Same Day Shipping Speed',
                'purchases:_1d_shipping_speed': 'Purchases: 1D Shipping Speed',
                'purchases:_2d_shipping_speed': 'Purchases: 2D Shipping Speed',
                'reporting_date': 'Reporting Date',
                'year': 'year',
                'week': 'week'}

    df_columns_config = {
                    'Search Query': st.column_config.TextColumn(
                        pinned=True
                    ),
                    'Search Query Volume': st.column_config.NumberColumn(
                        help='Search Query Volume',
                        format='localized',
                    ),
                    'Impressions: Total Count': st.column_config.NumberColumn(
                        help='How many asins were shown for the search query',
                        format='localized',
                    ),
                    'Clicks: Total Count': st.column_config.NumberColumn(
                        help='Total number of clicks for the search query',
                        format='localized',
                    ),
                    'Cart Adds: Total Count': st.column_config.NumberColumn(
                        help='Total number of cart adds for the search query',
                        format='localized',
                    ),
                    'Purchases: Total Count': st.column_config.NumberColumn(
                        help='Total number of purchases for the search query',
                        format='localized',
                    ),
                    'Impressions: Brand Count': st.column_config.NumberColumn(
                        help="How many brand's asins were shown for the search query",
                        format='localized',
                    ),
                    'Clicks: Brand Count': st.column_config.NumberColumn(
                        help="Number of clicks for the brand's asins",
                        format='localized',
                    ),
                    'Cart Adds: Brand Count': st.column_config.NumberColumn(
                        help="Number of cart adds for the brand's asins",
                        format='localized',
                    ),
                    'Purchases: Brand Count': st.column_config.NumberColumn(
                        help="Number of purchases for the brand's asins",
                        format='localized',
                    ),
                    'ASINs shown': st.column_config.NumberColumn(
                        help='number of Asins shown per each search query - in other words, the spots you need to be in in order to be seen',
                        format='%.0f',
                    ),
                    'Clicks: Price (Median)': st.column_config.NumberColumn(
                        help='Median price of products clicked on',
                        format='dollar',
                    ),
                    'Cart Adds: Price (Median)': st.column_config.NumberColumn(
                        help='Median price of products added to cart',
                        format='dollar',
                    ),
                    'Purchases: Price (Median)': st.column_config.NumberColumn(
                        help='Median price of products purchased',
                        format='dollar',
                    ),
                    'Clicks: Brand Price (Median)': st.column_config.NumberColumn(
                        help="Median price of a brand's products clicked on",
                        format='dollar',
                    ),
                    'Cart Adds: Brand Price (Median)': st.column_config.NumberColumn(
                        help="Median price of a brand's products added to cart",
                        format='dollar',
                    ),
                    'Purchases: Brand Price (Median)': st.column_config.NumberColumn(
                        help="Median price of a brand's products purchased",
                        format='dollar',
                    ),
                    'ASINs glance rate': st.column_config.NumberColumn(
                        help="Share of impressions that were shown for the brand's asins. Less than 100% means lost impressions",
                        format='percent',
                    ),
                    'KW ctr': st.column_config.NumberColumn(
                        help='Click-through rate for the search query',
                        format='percent',
                    ),
                    'ASIN ctr': st.column_config.NumberColumn(
                        help="Click-through rate for the brand's asins",
                        format='percent',
                    ),
                    'KW ATC %': st.column_config.NumberColumn(
                        help="Click to add-to-cart conversion rate for the search query",
                        format='percent',
                    ),
                    'ASINs ATC %': st.column_config.NumberColumn(
                        help="Click to add-to-cart conversion rate for the brand's asins",
                        format='percent',
                    ),
                    'KW ATC conversion': st.column_config.NumberColumn(
                        help="Add-to-cart to purchase conversion rate for the search query",
                        format='percent',
                    ),
                    'ASINs ATC conversion': st.column_config.NumberColumn(
                        help="Add-to-cart to purchase conversion rate for the brand's asins",
                        format='percent',
                    ),
                    'KW conversion': st.column_config.NumberColumn(
                        help="Total conversion rate for the search query (purchases / clicks)",
                        format='percent',
                    ),
                    'ASINs conversion': st.column_config.NumberColumn(
                        help="Brand's total conversion rate (purchases / clicks)",
                        format='percent',
                    )
            }

    combined_result_asin: dict = {
        "Weekly":{str(year): {} for year in range(2020, 2030)},
        "Monthly":{str(year): {} for year in range(2020, 2030)},
        "Quarterly":{str(year): {} for year in range(2020, 2030)}}
    combined_result_brand: dict = {
        "Weekly":{str(year): {} for year in range(2020, 2030)},
        "Monthly":{str(year): {} for year in range(2020, 2030)},
        "Quarterly":{str(year): {} for year in range(2020, 2030)}}

    user_folder = ''

    def session_state_decorator(func): #obsolete, use st.session_state decorator instead
        """Decorator save function's output to session state."""
        def wrapper(*args, **kwargs):
            name = kwargs.pop('name') if 'name' in kwargs else 'result'
            st.session_state[name] = func(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper

    @st.cache_resource(show_spinner=False)
    def pull_dates(result = None):
        with gc.gcloud_connect() as client:
            query = '''SELECT DISTINCT (week,year) as weekyear, week, year, reporting_date FROM `auxillary_development.sqp_brand_weekly`'''
            result = client.query(query).to_dataframe()
            del result['weekyear']
            result = result.sort_values('reporting_date')
        return result

    def is_similar(query, target, threshold):
        """Check if the query is similar to the target string using fuzzy matching."""
        words = query.lower().split()
        targets = target.lower().split()

        if all([any([fuzz.ratio(search_term, word)>=70 for word in words]) for search_term in targets]):
            return True
        return False

    @session_state_decorator
    @st.cache_resource(show_spinner=False)
    def read_bq(start_week:str="2025-01-01", end_week:str="2025-12-31", *args, **kwargs)-> None:
        """Read data from BigQuery and return a DataFrame."""
        with gc.gcloud_connect() as client:
            query = f'''SELECT * FROM `auxillary_development.sqp_brand_weekly` WHERE reporting_date BETWEEN "{start_week}" AND "{end_week}"'''
            result = client.query(query).to_dataframe()
            result = result.rename(columns=renaming)
        # st.session_state['bq_data'] = result.copy()
        return result
        
    def push_to_bq(file_list):
        """Push downloaded SQP Brand weekly report to BigQuery."""
        total_df = pd.DataFrame()
        for file in file_list:
            check_file(file, scope='bq')
            file.seek(0)
            header = pd.read_csv(file, nrows=1)
            columns = header.columns.tolist()
            sqp = process_header_columns(columns)
            file.seek(0)
            temp = pd.read_csv(file, skiprows=1)
            year = int(sqp['year'])
            week = int(sqp['week'].split(' ')[1])
            temp[['year','week']] = [year, week]
            total_df = pd.concat([total_df, temp])
        del total_df['Search Query Score']
        gc.normalize_columns(total_df)
        total_df = total_df.sort_values(['reporting_date','search_query_volume'], ascending=[True,False])

        with gc.gcloud_connect() as client:
            dates = total_df['reporting_date'].unique().tolist()
            dates_str = '","'.join(dates)
            query = f'''DELETE FROM `auxillary_development.sqp_brand_weekly` WHERE reporting_date IN ("{dates_str}")'''
            result = client.query(query)
            while result.running():
                st.toast('Wait, deleting rows')
                time.sleep(2)
                result.reload()
            st.toast(f'Deleted {result.num_dml_affected_rows} rows from the table, pushing new data')
            pandas_gbq.to_gbq(total_df, 'auxillary_development.sqp_brand_weekly', if_exists='append', bigquery_client=client)
        st.balloons()
        st.toast(f'Pushed {total_df.shape[0]} rows to the table')
        return

    def check_file(file, scope: Literal['general', 'bq'] = 'general') -> None:
        """Check if the file is a valid SQP file."""
        if isinstance(file, str):
            filename = file_list
        else:
            filename = file.name
        if not os.path.splitext(filename)[1]=='.csv':
            st.error(BaseException(f"Files must be csv:\n{filename}"))
            raise BaseException(f"Files must be csv:\n{filename}")
        test = pd.read_csv(file)
        condition = ("ASIN" in test.columns.tolist()[0] or "Brand" in test.columns.tolist()[0]) if scope == 'general' else ("Brand" in test.columns.tolist()[0])
        if not condition:
            st.error(BaseException(f"Wrong / non-SQP file provided:\n{filename}"))
            raise BaseException(f"Wrong / non-SQP file provided:\n{filename}")

    def process_header_columns(columns: list):# -> Dict[str, list[str] | int | str]:
        """Process the header columns to extract relevant information."""
        asin = re.findall('"(.*?)"', columns[0])[0]
        timeframe = re.findall('"(.*?)"', columns[1])[0]
        scope = "asin" if "ASIN" in columns[0] else "brand"
        if timeframe == "Weekly":
            year = re.findall('(2[0-90]{3})', columns[2])[-1]
            week = re.findall('"(.*?)"', columns[2])[0]
            return { scope: [asin], "timeframe": timeframe, "year": year, "week": week }
        elif timeframe == "Monthly":
            year = re.findall('"(.*?)"', columns[2])[0]
            month = re.findall('"(.*?)"', columns[3])[0]
            return { scope: [asin], "timeframe": timeframe, "year": year, "month": month }
        elif timeframe == "Quarterly":
            year = re.findall('"(.*?)"', columns[2])[0]
            quarter = re.findall('"(.*?)"', columns[3])[0]
            return { scope: [asin], "timeframe": timeframe, "year": year, "quarter": quarter }
        else:
            return {scope: "not found", "timeframe": "unknown", "year": 0, "quarter": 0}

    def sort_files(file_list: list) -> None:
        """"Sort the files into the combined result dictionaries."""
        duplicates = []
        for file in file_list:
            check_file(file)
            header = pd.read_csv(file, nrows=1)
            columns = header.columns.tolist()
            sqp = process_header_columns(columns)
            if not sqp in duplicates: #check for duplicated files just in case
                duplicates.append(dict(sqp))
            else:
                raise BaseException(f"Duplicate file found:\n{file}\n{sqp}")
            
            if 'asin' in sqp:
                target_dict: dict = combined_result_asin
                scope = 'asin'
            elif 'brand' in sqp:
                target_dict: dict = combined_result_brand
                scope = 'brand'
            else:
                target_dict = {}
                scope = 'unknown'
                
            sqp['filepath'] = [file]
            if sqp['timeframe'] == "Weekly":
                year = sqp['year']
                week = sqp['week']
                if week in target_dict['Weekly'][year]:
                    target_dict['Weekly'][year][week][scope].extend(sqp[scope])
                    target_dict['Weekly'][year][week]['filepath'].extend(sqp['filepath'])
                else:
                    target_dict['Weekly'][year][week] = sqp
            elif sqp['timeframe'] == "Monthly":
                year = sqp['year']
                month = sqp['month']
                if month in target_dict['Monthly'][year]:
                    target_dict['Monthly'][year][month][scope].extend(sqp[scope])
                    target_dict['Monthly'][year][month]['filepath'].extend(sqp['filepath'])
                else:
                    target_dict['Monthly'][year][month] = sqp
            elif sqp['timeframe'] == "Quarterly":
                year = sqp['year']
                quarter = sqp['quarter']
                if quarter in target_dict['Quarterly'][year]:
                    target_dict['Quarterly'][year][quarter][scope].extend(sqp[scope])
                    target_dict['Quarterly'][year][quarter]['filepath'].extend(sqp['filepath'])
                else:
                    target_dict['Quarterly'][year][quarter] = sqp
        return

    def filter_dicts(files_dict: dict) -> dict:
        """Filter the dictionaries to remove empty entries."""
        clean = {"Weekly":{}, "Monthly":{}, "Quarterly":{}}
        for timeframe in ("Weekly", "Monthly", "Quarterly"):
            temp_dict = files_dict[timeframe]
            for year in temp_dict:
                if temp_dict[year]:
                    clean[timeframe][year] = temp_dict[year]
        return {key:value for key, value in clean.items() if value}

    def refine_file(df: pd.DataFrame, scope:Literal['asin','brand']='asin') -> pd.DataFrame:
        """Refine the DataFrame by calculating additional metrics."""
        entity='ASIN' if scope=='asin' else 'Brand'
        df['ASINs shown'] = df['Impressions: Total Count'] / df['Search Query Volume']
        df['ASINs glance rate'] = df[f'Impressions: {entity} Count'] / df['Search Query Volume']
        df['KW ctr'] = df['Clicks: Total Count'] / df['Impressions: Total Count']
        df['ASIN ctr'] = df[f'Clicks: {entity} Count'] / df[f'Impressions: {entity} Count']
        df['KW ATC %'] = df['Cart Adds: Total Count'] / df['Clicks: Total Count']
        df['ASINs ATC %'] = df[f'Cart Adds: {entity} Count'] / df[f'Clicks: {entity} Count']

        df['KW ATC conversion'] = df['Purchases: Total Count'] / df['Cart Adds: Total Count']
        df['ASINs ATC conversion'] = df[f'Purchases: {entity} Count'] / df[f'Cart Adds: {entity} Count']

        df['KW conversion'] = df['Purchases: Total Count'] / df['Clicks: Total Count']
        df['ASINs conversion'] = df[f'Purchases: {entity} Count'] / df[f'Clicks: {entity} Count']
        return df.fillna(0)

    def combine_files(
            dfs: list,
            scope:Literal['asin','brand']='asin',
            column:Literal['Search Query', 'Reporting Date'] = 'Search Query'
            ) -> pd.DataFrame:
        """Combine multiple DataFrames into one and calculate additional metrics."""
        entity='ASIN' if scope=='asin' else 'Brand'
        agg_func = 'min' if scope=='asin' else 'sum'
        sum_cols_asin = [
            f'Impressions: {entity} Count',f'Clicks: {entity} Count',
            f'Cart Adds: {entity} Count',f'Purchases: {entity} Count',
            'median_click_product','median_atc_product','median_purchase_product'
            ]
        immutable_cols = [
            'Search Query Volume','Impressions: Total Count', 'Clicks: Total Count',
            'Cart Adds: Total Count','Purchases: Total Count',
            'median_click_total', 'median_atc_total', 'median_purchase_total'
            ]
        
        total = pd.concat(dfs).fillna(0)

        total['median_click_total'] = total['Clicks: Price (Median)'] * total['Clicks: Total Count']
        total['median_atc_total'] = total['Cart Adds: Price (Median)'] * total['Cart Adds: Total Count']
        total['median_purchase_total'] = total['Purchases: Price (Median)'] * total['Purchases: Total Count']
        
        total['median_click_product'] = total[f'Clicks: {entity} Price (Median)'] * total[f'Clicks: {entity} Count']
        total['median_atc_product'] = total[f'Cart Adds: {entity} Price (Median)'] * total[f'Cart Adds: {entity} Count']
        total['median_purchase_product'] = total[f'Purchases: {entity} Price (Median)'] * total[f'Purchases: {entity} Count']
        

        common_df = total.groupby(column)[immutable_cols].agg(agg_func).reset_index()
        asin_df = total.groupby(column)[sum_cols_asin].agg('sum').reset_index()
        
        common_df['Clicks: Price (Median)'] = common_df['median_click_total'] / common_df['Clicks: Total Count']
        common_df['Cart Adds: Price (Median)'] = common_df['median_atc_total'] / common_df['Cart Adds: Total Count']
        common_df['Purchases: Price (Median)'] = common_df['median_purchase_total'] / common_df['Purchases: Total Count']

        asin_df[f'Clicks: {entity} Price (Median)'] = asin_df['median_click_product'] / asin_df[f'Clicks: {entity} Count']
        asin_df[f'Cart Adds: {entity} Price (Median)'] = asin_df['median_atc_product'] / asin_df[f'Cart Adds: {entity} Count']
        asin_df[f'Purchases: {entity} Price (Median)'] = asin_df['median_purchase_product'] / asin_df[f'Purchases: {entity} Count']
        
        summary = pd.merge(common_df, asin_df, how='outer', on=column, validate="1:1").fillna(0)

        for col in ('median_click_product','median_atc_product','median_purchase_product',
                    'median_click_total','median_atc_total','median_purchase_total'):
            del summary[col]
        
        return summary

    def export_sqps(sqp_dict, scope:Literal['asin','brand']='asin'):
        """Export the SQP data to Excel files."""
        for timeframe in sqp_dict:
            with pd.ExcelWriter(os.path.join(user_folder, f'SQP_{scope}_{timeframe}.xlsx'), engine = 'xlsxwriter') as writer:
                for year in sqp_dict[timeframe]:
                    for period in sqp_dict[timeframe][year]:
                        reporting_range = period.split('|')[0].strip()
                        sheet_name = f'{year} - {reporting_range}'
                        entities = ', '.join(sqp_dict[timeframe][year][period][scope])
                        dfs = [pd.read_csv(file, skiprows=1) for file in sqp_dict[timeframe][year][period]['filepath']]
                        combined = combine_files(dfs, scope)
                        summary = refine_file(combined.copy(), scope)
                        entity_row = pd.DataFrame([f'SQP analysis for: {entities}'], columns=['Search Query'])
                        
                        summary = pd.concat([summary, entity_row], axis=0, ignore_index=True)
                        summary.to_excel(writer, sheet_name = sheet_name, index=False)
                        ff.format_header(summary, writer, sheet_name)
        


    #############################################################################gui section#####################################################
    if 'search_term' not in st.session_state:
        st.session_state['search_term'] = None

    @st.fragment
    def create_bytes_df(dfs, sheet_names, **kwargs):
        df_bytes = ff.prepare_for_export(
            dfs, sheet_names,
            numeric_cols=['Search Query Volume','Impressions: Total Count','Clicks: Total Count','Cart Adds: Total Count','Purchases: Total Count',
                            'Impressions: Brand Count','Clicks: Brand Count','Cart Adds: Brand Count','Purchases: Brand Count','ASINs shown'],
            currency_cols=['Clicks: Price (Median)','Cart Adds: Price (Median)','Purchases: Price (Median)','Clicks: Brand Price (Median)',
                            'Cart Adds: Brand Price (Median)','Purchases: Brand Price (Median)'],
            percent_cols=['ASINs glance rate','KW ctr','ASIN ctr','KW ATC %','ASINs ATC %','KW ATC conversion','ASINs ATC conversion',
                            'KW conversion','ASINs conversion'])
        return df_bytes

    @st.fragment
    def filter_df(search_term, threshold=70):
        bq = st.session_state['bq_data'].copy()
        kw = st.session_state['kw_records'].copy() if 'kw_records' in st.session_state else pd.DataFrame()
        if search_term:
            bq = bq[bq['Search Query'].apply(lambda x: is_similar(x, search_term, threshold))]
            kw = kw[kw['search_term'].apply(lambda x: is_similar(x, search_term, threshold))]
        st.session_state['filtered_bq'] = bq.copy()
        st.session_state['kw_filtered'] = kw.copy()

    @st.fragment
    def create_figure(
            df,
            title='Search Query Volume and KW Conversion Over Time',
            right_axis='percentage',
            **kwargs):
        left_lines = [kwargs[x] for x in kwargs if 'left' in x]
        right_lines = [kwargs[x] for x in kwargs if 'right' in x]
        colors_left = ['blue', 'green', 'red', 'orange']
        colors_right = ['purple', 'pink', 'brown', 'gray']
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        for i,left in enumerate(left_lines):
            fig.add_trace(
                go.Scatter(x=df['Reporting Date'], y=df[left], name=left, line=dict(color=colors_left[i])),
                secondary_y=False,
                )
        for i, right in enumerate(right_lines):
            fig.add_trace(
                go.Scatter(x=df['Reporting Date'], y=df[right], name=right, line=dict(color=colors_right[i])),
                secondary_y=True,
            )

        fig.update_layout(
            title_text=title
        )

        fig.update_xaxes(title_text="Reporting Date")

        fig.update_yaxes(title_text=left_lines[0], secondary_y=False)
        if len(right_lines)>0 and right_axis=='percentage':
            fig.update_yaxes(title_text=right_lines[0], secondary_y=True, tickformat=".1%")
        return fig


    controls_area = sqp_tab.container()
    plots_area_top = sqp_tab.empty()
    plots_area_bottom = sqp_tab.empty()
    plot1, plot2 = plots_area_top.columns([1,1], gap='small')
    plot3, plot4 = plots_area_bottom.columns([1,1], gap='small')

    df_area = sqp_tab.empty()
    with st.spinner('Retrieving dates...', show_time=True):
        dates = pull_dates()
        dates['reporting_date'] = pd.to_datetime(dates['reporting_date']).dt.date
        dates_list = dates['reporting_date'].unique().tolist()
        start_date = dates_list[-8]
        end_date = dates_list[-1]

    selected_dates = slider_area.select_slider(
        'Select the date range for the SQP data',
        options=dates_list,
        value=(start_date, end_date),
        key='date_range'
    )
    if selected_dates:
        if button_area.button('Pull SQP data', key='pull_sqp_data', on_click=read_bq, args=(selected_dates[0], selected_dates[1]), kwargs=({'name':'bq_data'}), disabled=False):
            st.session_state['filtered_bq'] = st.session_state['bq_data'].copy()
        def update_search_term():
            st.session_state['search_term'] = st.session_state['keyword_input']
            filter_df(st.session_state['search_term'])
            st.session_state.update({'export_sqp_data': False})

        kw_filter_area.text_input(
            'Search for a specific keyword',
            placeholder='Enter a keyword to filter the SQP data' if 'bq_data' in st.session_state else 'Please pull SQP data first',
            disabled=False if 'bq_data' in st.session_state else True,
            key='keyword_input',
            on_change=update_search_term
        )
        
        if 'bq_data' in st.session_state:
            bq = st.session_state['filtered_bq'].copy()if 'filtered_bq' in st.session_state else st.session_state['bq_data'].copy()
            
            bq_dates = combine_files([bq], scope='brand', column='Reporting Date')
            bq_search = combine_files([bq], scope='brand', column='Search Query')
            bq_dates = refine_file(bq_dates, scope='brand')
            bq_search = refine_file(bq_search, scope='brand')
            df_area.dataframe(
                bq_search.sort_values('Purchases: Total Count', ascending=False),
                use_container_width=True,
                hide_index=True,
                key='bq_search',
                column_config=df_columns_config)
        
            fig1 = create_figure(bq_dates, title="Search performance over time", left1='Search Query Volume', left2 = 'Clicks: Brand Count', right1='KW ctr', right2='ASIN ctr')
            fig2 = create_figure(bq_dates, title="Add-to-cart performance over time", left1='Cart Adds: Total Count', left2='Cart Adds: Brand Count', right1='KW ATC %', right2='ASINs ATC %')
            fig3 = create_figure(bq_dates, title="Purchases", left1='Purchases: Total Count', left2='Purchases: Brand Count',right1='KW conversion', right2='ASINs conversion')
            fig4 = create_figure(bq_dates, title="Pricing", left1='Clicks: Price (Median)', left2='Cart Adds: Price (Median)', left3='Purchases: Price (Median)', left4='Purchases: Brand Price (Median)')


            plot1.plotly_chart(fig1, use_container_width=True)
            plot2.plotly_chart(fig2, use_container_width=True)
            plot3.plotly_chart(fig3, use_container_width=True)
            plot4.plotly_chart(fig4, use_container_width=True)

            if sqp_tab.checkbox('Export SQP data to Excel', value=False, key='export_sqp_data'):
                with st.spinner('Preparing data for download...', show_time=True):
                    st.download_button(
                        label="Download SQP data",
                        data=create_bytes_df([bq_dates, bq_search],['Reporting Date', 'Search Query']),
                        file_name='SQP_data.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key='download_sqp_data',
                        on_click=lambda: st.session_state.update({'export_sqp_data': False})
                        )

    if user_email=='sergey@mellanni.com':
        if sqp_tab.button('Push SQP data to BigQuery'):
            file_upload = st.file_uploader(
                label='Upload SQP files',
                type=['csv'],
                accept_multiple_files=True,
                key='sqp_files'
            )
            st.cache_resource.clear()
        if 'sqp_files' in st.session_state and len(st.session_state['sqp_files'])>0:
            file_list = st.session_state['sqp_files']
            with st.spinner('Processing files...', show_time=True):
                push_to_bq(file_list)
                st.success('Files processed and pushed to BigQuery successfully!')


    ########## Keywords tab ------------------------------------------------------------
    # kw_tab.write('This tab is under development, please check back later.')

    kw_columns_config = {
            'Reporting Date': st.column_config.DateColumn(
                format='YYYY-MM-DD',
                help='Date of the keyword data'
            ),
            'Position': st.column_config.NumberColumn(
                help='Average weighted position of the keyword',
                format='%.1f'
            ),
            'purchases_total_count': st.column_config.NumberColumn(
                help='Total number of purchases for the keyword',
                format='localized'
            ),
            'purchases_brand_count': st.column_config.NumberColumn(
                help='Total number of brand purchases for the keyword',
                format='localized'
            ),
            'search_term': st.column_config.TextColumn(
                help='Search term for the keyword',
                pinned=True
            )
        }

    @st.cache_resource(show_spinner=True)
    def pull_keywords_from_bq(list_of_dates) -> pd.DataFrame:
        """Pull keywords data from BigQuery."""
        dates_str = '","'.join([d.strftime("%Y-%-m-%d") for d in list_of_dates])
        with gc.gcloud_connect() as client:
            query = f'''
            SELECT k.search_term, k.ASIN, k.Position, k.date, d.collection,
            FROM `auxillary_development.keywords_us` as k
            LEFT JOIN (
                SELECT DISTINCT ASIN, collection
                FROM `auxillary_development.dictionary`
                ) AS d ON k.ASIN = d.ASIN
            WHERE DATE(k.date) IN ("{dates_str}")
            '''
            result = client.query(query).to_dataframe()
            # print(len(result))
            result = result.groupby(['date', 'ASIN', 'search_term']).agg('min').reset_index()
            # print(len(result))
            return result
    
    if selected_dates and 'bq_data' in st.session_state:

        kw_records = pull_keywords_from_bq(
            dates_list[dates_list.index(selected_dates[0]):dates_list.index(selected_dates[1])+1]
            )
        sqp_data = st.session_state['bq_data'][['Search Query','Purchases: Total Count','Purchases: Brand Count','Reporting Date']].copy()
        sqp_data = sqp_data.rename(
            columns={
                'Search Query': 'search_term',
                'Purchases: Total Count': 'purchases_total_count',
                'Purchases: Brand Count': 'purchases_brand_count'})
        kw_records = kw_records.rename(columns={'date': 'Reporting Date'})
        kw_records = pd.merge(kw_records, sqp_data, how='left', on=['search_term', 'Reporting Date']).fillna(0)
        kw_records['prod'] = kw_records['Position'] * kw_records['purchases_total_count']
        st.session_state['kw_records'] = kw_records.copy()
        
        if "kw_filtered" in st.session_state:
            kw_filtered = st.session_state['kw_filtered'].copy()
            kw_daily = st.session_state['kw_filtered'].copy()
        else:
            kw_filtered = kw_records.copy()
            kw_daily = kw_records.copy()
        kw_filtered = kw_filtered.groupby(['Reporting Date']).agg(
            {'prod': 'sum', 'purchases_total_count': 'sum','purchases_brand_count': 'sum'}).reset_index()
        kw_filtered['Position'] = kw_filtered['prod'] / kw_filtered['purchases_total_count']
        del kw_filtered['prod']
        kw_filtered = kw_filtered.sort_values('Reporting Date', ascending=False)

        kw_daily = kw_daily.groupby(['Reporting Date', 'search_term']).agg(
            {'prod': 'sum', 'purchases_total_count': 'sum','purchases_brand_count': 'sum'}).reset_index()
        kw_daily['Position'] = kw_daily['prod'] / kw_daily['purchases_total_count']
        del kw_daily['prod']
        kw_daily = kw_daily.sort_values(['Reporting Date', 'purchases_total_count'], ascending=False)

        kw_df1.markdown('***By date***')
        kw_df1.dataframe(kw_filtered, hide_index=True, use_container_width=True, column_config=kw_columns_config)
        kw_df2.markdown('***By keyword***')
        kw_df2.dataframe(kw_daily, hide_index=True, use_container_width=True, column_config=kw_columns_config)


        kw_fig1 = create_figure(
            kw_filtered,
            title='Average weighted position and purchases over time',
            right_axis='absolute',
            right1='Position',
            left1='purchases_total_count',
        )

        kw_plot_area.plotly_chart(kw_fig1, use_container_width=True)
        
