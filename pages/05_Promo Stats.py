import streamlit as st
import pandas as pd
import re
# import login
# from io import BytesIO
from google.cloud import bigquery #pip install google-cloud-bigquery
from google.oauth2 import service_account
from modules import gcloud_modules as gc
from modules import formatting as ff
import pytz
pacific = pytz.timezone('US/Pacific')

st.set_page_config(page_title = 'M Tools App', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state = 'collapsed')

# st.session_state['login'], st.session_state['username']= login.login()

import login_google
st.session_state['login'] = login_google.login()

if st.session_state['login'][0]:
# if True:

    bad_chars = [
        '%off any%',
        '%off for non-prime customers%',
        'AB DEX Incentives%',
        'ABMarketing:%',
        'ABMktg%',
        'Acquisition Promotion for Prime Day',
        'ADEX%',
        'AFD Base Promo%',
        'Discover PAGE%',
        'EFF Promotion%',
        'Exports Free Shipping',
        'FAP offer%',
        'First App purchase%',
        'Free Delivery On First Order%',
        'Free Same Day%',
        'Free Sub SameDay%',
        'PAGE-Venmo%',
        'PD21 BXGY',
        'PROD_%',
        'Project Diamond%',
        '%AB Incentives%',
        'SameDay US%',
        'Promo Propensity%',
        'VPC-%',
        'TDU Promotion%',
        'US Core Free Shipping%',
        'USAA PAGE%',
        'User Activation Promotion%',
        'Venmo-Maple%'
        ]

    ld_promos = [
        'DCMS%', 'Mellanni%'
        ]

    negative_filter = bad_chars+ld_promos
    negative_filter = [x.replace('%','') for x in negative_filter]

    @st.cache_data(show_spinner=False)
    def read_promos(
        report = 'reports',
        table = 'promotions',
        column = 'description',
        code_list = None,
        start = None, end = None,
        coupons = False
        ):
        prefix_sql = f'SELECT shipment_date, description, amazon_order_id, item_promotion_discount FROM `{report}.{table}`'
        if coupons:
            negative_filter.remove('VPC-')
            negative_filter.remove('DCMS')
            negative_filter.remove('Mellanni')
        negative_str = f'''WHERE NOT REGEXP_CONTAINS({column},"{'|'.join(negative_filter)}")'''

        query = f'{prefix_sql} {negative_str}'
        if code_list:
            code_str = f''' AND REGEXP_CONTAINS({column},"{'|'.join(code_list)}")'''
            query += code_str
        if all([start is not None, end is not None]):
            start, end = pd.to_datetime(start).date(), pd.to_datetime(end).date()
            date_str = f' AND (DATE(shipment_date) >= DATE("{start}") AND DATE(shipment_date) <= DATE("{end}"))'
            query += date_str

        client = gc.gcloud_connect()
        query_job = client.query(query)  # Make an API request.
        data = query_job.result().to_dataframe()
        client.close()
        return data

    @st.cache_data(show_spinner=False)
    def read_all_orders(
        order_list,
        report = 'reports',
        table = 'all_orders',
        skus = False
        ) -> pd.DataFrame:
        '''
        Read rows from all_order report from cloud targeting order from "order_list" - 
        - pre-selected orders from promo report

        Parameters
        ----------
        db_path : STR
            path to all_orders.db file.
        order_list : list
            List of orders to select from all_orders.db file.

        Returns
        -------
        orders : pd.DataFrame
            selected rows from all_orders.db file limited to pre-defined columns.
        '''
        column_list = ['amazon_order_id','purchase_date','order_status','fulfillment_channel',
        'sku','asin','quantity','currency','item_price','item_promotion_discount',
        'promotion_ids','is_business_order','buyer_company_name']
        order_str = '","'.join(order_list)
        column_str = ', '.join(column_list)
        if skus:
            chunk_size = 100_000
            chunks = len(order_list)//chunk_size+1
            order_chunks = []
            for c in range(chunks):
                chunk = order_list[c*chunk_size:(c+1)*chunk_size]
                order_chunks.append(chunk)
            df = pd.DataFrame()

            query = f'''SELECT
                            asin,
                            SUM(CAST(quantity AS INT)) as quantity,
                            SUM(CAST(item_price AS FLOAT64)) as sales,
                            SUM(CAST(item_promotion_discount AS FLOAT64)) as discount
                        FROM `{report}.{table}`
                        WHERE amazon_order_id IN UNNEST (@orders)
                        GROUP BY asin'''
                        # ORDER BY sales
                        # DESC
                        # '''
            client = gc.gcloud_connect()
            for chunk in order_chunks:
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ArrayQueryParameter("orders", "STRING", chunk),
                    ]
                )

                query_job = client.query(query, job_config=job_config)  # Make an API request.
                orders = query_job.result().to_dataframe()
                df = pd.concat([df, orders])
            client.close()
            df = df.pivot_table(values = ['quantity', 'sales', 'discount'], index = 'asin',aggfunc = 'sum').reset_index()
            
        else:
            query = f'''SELECT {column_str} FROM `{report}.{table}` WHERE amazon_order_id IN UNNEST (@orders)'''
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("orders", "STRING", order_list),
                ]
            )
            client = gc.gcloud_connect()
            query_job = client.query(query, job_config=job_config)  # Make an API request.
            orders = query_job.result().to_dataframe()
            client.close()
        if skus:
            df.rename(columns = {'sales':'Sales, $', 'discount':'Discount, $'}, inplace = True)
            return df
        orders['purchase_date'] = orders['purchase_date'].dt.tz_convert(pacific).dt.tz_localize(None).dt.date
        orders['item_price'] = orders['item_price'].astype('float')
        orders['item_promotion_discount'] = orders['item_promotion_discount'].astype('float')
        orders['quantity'] = orders['quantity'].astype('int')
        orders_pivot = orders.pivot_table(
            values = ['item_price','quantity'],
            index = ['amazon_order_id','purchase_date'],
            aggfunc = 'sum'
            )#.reset_index()
        return orders_pivot

    @st.cache_data(show_spinner= False)
    def read_attribution(
        report = 'reports',
        table = 'attribution',
        start = None, end = None
        ):
        query =f'SELECT * FROM `{report}.{table}` WHERE DATE(date) BETWEEN DATE("{start}") AND DATE("{end}")'
        client = gc.gcloud_connect()
        query_job = client.query(query)  # Make an API request.
        data = query_job.result().to_dataframe()
        client.close()
        data['date'] = pd.to_datetime(data['date'], format = 'mixed', yearfirst=True)
        data = data.sort_values('date')
        data = data.rename(columns={'adGroupId':'ad_group_name','totalAttributedSales14d':'Sales, $','totalUnitsSold14d':'quantity'})
        numerics = ['int','float']
        num_cols = data.select_dtypes(include = numerics).columns
        float_cols = data.select_dtypes('float').columns
        # int_cols = data.select_dtypes('int').columns
        data_pivot = data.pivot_table(
            values = num_cols,
            index = 'ad_group_name',
            aggfunc = 'sum'
            ).reset_index()
        data_pivot[float_cols] = round(data_pivot[float_cols],2)
        # data_pivot.rename(columns = {'_14_day_total_sales':'Sales, $','_14_day_total_units_sold':'quantity'}, inplace = True)
        data_pivot['Discount, $'] = 0
        data_pivot = data_pivot.sort_values('Sales, $', ascending = False)
        return data_pivot, data

    @st.cache_data(show_spinner=False)
    def process_data(code_list = None, start = None, end = None, coupons = False, skus = False):
        def sort_and_split(x):
            x = [i for i in x if i != ' ']
            x = set(x)
            x = sorted(x)
            x = ' | '.join(x)
            return x
        if all([start is not None, end is not None]):
            spinner_str = f'Pulling promo report for {(end-start).days + 1} days'
        else:
            spinner_str = 'Pulling full promo report'
        with st.spinner(spinner_str):
            promos = read_promos(code_list=code_list, start = start, end = end, coupons = coupons)
            code_pattern = r'\(([A-Za-z0-9\s]{8,13})\-{0,1}\d{0,1}\)'
            promos['promo_code'] = promos['description'].str.extract(code_pattern).fillna(' ')
            promos['promo_code'] = promos['promo_code'].str.strip()
            if code_list != None:
                promos = promos[promos['promo_code'].isin(code_list)]

            promos_pivot = promos.pivot_table(
                values = ['item_promotion_discount','description','promo_code'],
                index = ['amazon_order_id'],
                aggfunc = {'item_promotion_discount':'sum',
                        'description':sort_and_split,
                        'promo_code':sort_and_split}
                )
            order_list = promos_pivot.index.tolist()
            if len(order_list) == 0:
                total = 'Sorry, no data for this time period yet'
                full = 'Sorry, no data for this time period yet'
            else:
                with st.spinner(f'Pulling {len(order_list)} orders'):
                    orders_pivot = read_all_orders(order_list, skus = skus)

                    if skus:
                        orders_pivot['Net proceeds'] = orders_pivot['Sales, $'] - orders_pivot['Discount, $']
                        orders_pivot['Discount, %'] = round(orders_pivot['Discount, $'] / orders_pivot['Sales, $'] * 100, 1)
                        return orders_pivot, orders_pivot
                    
                    total = pd.merge(orders_pivot, promos_pivot, left_index = True, right_index = True).reset_index()
                    full = total.copy()
                    total = total.pivot_table(
                        values = ['item_price', 'quantity','item_promotion_discount'],
                        index = ['promo_code','description'],
                        aggfunc = 'sum').reset_index()
                    
                    total[['item_price','item_promotion_discount']] = round(total[['item_price','item_promotion_discount']] ,2)

                    total.rename(columns = {'item_price':'Sales, $', 'item_promotion_discount':'Discount, $'}, inplace = True)
                    total['Net proceeds'] = total['Sales, $'] - total['Discount, $']
                    total['Discount, %'] = round(total['Discount, $'] / total['Sales, $'] * 100, 1)
                    total = total.sort_values('quantity', ascending = False)

        return total, full

    # def prepare_for_export(dfs,sheet_names):
    #     output = BytesIO()
    #     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    #         for df,sheet_name in list(zip(dfs,sheet_names)):
    #             df.to_excel(writer, sheet_name = sheet_name, index = False)
    #             ff.format_header(df,writer,sheet_name)
    #     return output.getvalue()

    end = pd.to_datetime('today')
    start = end - pd.to_timedelta(180, 'days')

    col1, col2, col3 = st.columns([7,2,2])

    d_from = col3.date_input('Starting date', key = 'db_datefrom',value = start )
    d_to = col3.date_input('End date', key = 'db_dateto', value = end)
    coupons = col3.checkbox('Include coupons\n(will take MUCH longer)?')

    codes = re.split(' |,|\n',col2.text_area('Input codes to search'))
    if col2.button('Get promo\ncode stats'):
        st.session_state.file_name,st.session_state.sheet_name = 'Promo_report.xlsx','Promos'
        codes = [x for x in codes if x != '']
        with st.spinner('Please wait, pulling information...'):
            if codes == []:
                st.session_state.processed_data, st.session_state.full = process_data(code_list = None,start = d_from, end = d_to)
            else:
                st.session_state.processed_data, st.session_state.full = process_data(code_list = codes,start = d_from, end = d_to)
    if col2.button('Get Attribution data'):
        st.session_state.file_name,st.session_state.sheet_name = 'Attribution_report.xlsx',['Total','Daily']
        with st.spinner('Loading Attribution data'):
            data = read_attribution(start = d_from, end = d_to)
        st.session_state.processed_data = [data[0], data[1]]

    if col3.button('Get SKU data'):
        st.session_state.file_name,st.session_state.sheet_name = 'SKU_report.xlsx','SKUs'
        st.session_state.processed_data, st.session_state.full = process_data(code_list = None,start = d_from, end = d_to, coupons = coupons, skus = True)

    if 'processed_data' in st.session_state and not isinstance(st.session_state.processed_data,str):
        if isinstance(st.session_state.processed_data,list):
            display = st.session_state.processed_data[0]
            result = ff.prepare_for_export([st.session_state['processed_data'][0],st.session_state['processed_data'][1]],st.session_state.sheet_name)
        else:
            display = st.session_state.processed_data
            result = ff.prepare_for_export([st.session_state['processed_data'],st.session_state.full],[st.session_state.sheet_name,'Full data'])
        st.write(display)

        st.download_button('Download results',result, file_name = st.session_state.file_name)
        sales = round(display['Sales, $'].sum(),2)
        discount = round(display['Discount, $'].sum(),2)
        units = display['quantity'].sum()
        percentage = discount/sales
        metric1, metric2= col1.columns([1,1])
        metric1.metric('Total Sales and Units', "${:,}".format(sales))
        metric1.metric('Total Sales and Units',"{:,}".format(units), label_visibility='hidden')
        metric2.metric('Discount, $ and %', "${:,}".format(discount))
        metric2.metric('Discount, $ and %', "{:.1%}".format(percentage), label_visibility='hidden')


