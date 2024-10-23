import streamlit as st
import pandas as pd

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import numpy as np
from queue import Queue
from google.cloud import bigquery #pip install google-cloud-bigquery
from google.oauth2 import service_account
from modules import gcloud_modules as gc
from modules import formatting as ff
from io import BytesIO


import altair as alt
# from matplotlib import pyplot as plt

DAYS_TO_PULL = 60
START_DATE = (pd.to_datetime('today') - pd.Timedelta(days = DAYS_TO_PULL)).date().strftime('%Y-%m-%d')

st.set_page_config(page_title = 'Price tracker', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')

chart_area = st.container()
notes_area = st.container()
button_area = st.container()
asin_area = st.container()
col1,col2,col3,col4,col5,col6 = asin_area.columns([1,1,1,1,1,1])

notes_area.write('''*For some products you may see a "null" brand popping up - that is Amazon Basics not giving away it's data (or Mellanni hasn't launched yet)''')

def get_asins(queue,mode = 'mapping'):
    # authorize Google Sheets credentials
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    # creds_file = 'competitor_pricing.json'
    # if not os.path.isfile('competitor_pricing.json'):
    #     creds_file = input('Input path to creds file')#G:\Shared drives\70 Data & Technology\70.03 Scripts\mellanni_2\google-cloud\competitor_pricing.json
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets['gsheets-access'], scope)
    # creds = service_account.Credentials.from_service_account_info(st.secrets['gsheets-access'])
    client = gspread.authorize(creds)
    
    #open Google Sheets sheet
    book = client.open_by_url('https://docs.google.com/spreadsheets/d/12AD3N0eUWXt2YjY64OEJpj8IWRRxZA_Qq5TSZJ0gINQ')
    sheet = book.get_worksheet_by_id(28000141)
    data = pd.DataFrame(sheet.get_all_records(head = 2))
    data['ASIN'] = data['Link'].str.extract('([A-Z0-9]{10})')
    asin_cols = [x for x in data.columns if 'ASIN' in x]
    if mode == 'asins':
        asins = data[asin_cols].values.tolist()
        asins = list(set([asin for asin_list in asins for asin in asin_list]))
        # if '' in asins:
        #     asins.remove('')
        asins = [str(x) for x in asins if x != np.nan]
        asins = [x.strip() for x in asins if re.search('([A-Z0-9]{10})',x)]
        queue.put(asins)
        return None
    elif mode == 'mapping':
        products = data['Product'].unique().tolist()
        mapping = {}
        for product in products:
            product_asins = data[data['Product'] == product][['ASIN']+asin_cols].values[0].tolist()
            product_asins = [str(x) for x in product_asins if x != np.nan]
            product_asins = [x.strip() for x in product_asins if x != '']
            mapping[product] = product_asins
        queue.put(mapping)
        return None

def get_prices(queue, query):
        # start_date = (pd.to_datetime('today') - pd.Timedelta(days = 30)).date()
        client = gc.gcloud_connect()
        query_job = client.query(query)  # Make an API request.
        data = query_job.result().to_dataframe()
        client.close()
        data['datetime'] = pd.to_datetime(data['datetime'], format = '%Y-%m-%d %H:%M:%S')
        data = data.sort_values('datetime')
        data['final_price'] = data['final_price'].fillna('out of stock')
        queue.put(data)
        return None

if 'data' not in st.session_state:
# if st.button('Pull data'):

    query_short = '''SELECT datetime, asin, brand, final_price, image, coupon, full_price
                FROM `auxillary_development.price_comparison`
                WHERE DATE(datetime) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND CURRENT_DATE()'''
    query_long = f'''SELECT datetime, asin, brand, final_price, image, coupon, full_price
                FROM `auxillary_development.price_comparison`
                WHERE DATE(datetime) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {DAYS_TO_PULL} DAY) AND CURRENT_DATE()'''
    q1, q2, q3 = Queue(), Queue(), Queue()
    p1 = threading.Thread(target = get_asins,args = (q1,))
    p2 = threading.Thread(target = get_prices,args = (q2, query_short))
    # p3 = threading.Thread(target = get_prices,args = (q3, query_long))

    processes = [p1,p2]
    for process in processes:
        process.start()
    # p3.start()
    st.session_state.mapping = q1.get()
    st.session_state.prices = q2.get()
    # st.session_state.full_prices = q3.get()

    for process in processes:
        process.join()


    st.session_state.df = pd.DataFrame()
    for product,asins in st.session_state.mapping.items():
        temp_file = st.session_state.prices[st.session_state.prices['asin'].isin(asins)]
        temp_file['product'] = product
        st.session_state.df = pd.concat([st.session_state.df,temp_file])
        st.session_state.data = True

if 'data' in st.session_state:
    if button_area.button('Prepare export'):
        
        # p3.join()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.df.to_excel(writer, sheet_name = 'Prices', index = False)
            ff.format_header(st.session_state.df, writer, 'Prices')
        button_area.download_button('Export full data',output.getvalue(), file_name = 'Price history.xlsx')

    else:
        products = st.session_state.df['product'].unique().tolist()
        product = button_area.selectbox('Select a product',products)
        f = st.session_state.df[st.session_state.df['product'] == product]
        f['brandasin'] = f['brand'] + ' : ' + f['asin']
        f['link'] = 'https://www.amazon.com/dp/'+f['asin']
        plot_file = f[['datetime','brandasin','final_price']]
        link_file = f[['datetime','brand','asin','product','link','full_price','coupon','image','final_price']].copy()
        last_date = pd.to_datetime(f['datetime'].values.tolist()[-1])
        link_file = link_file[link_file['datetime'] == last_date].reset_index()

        c = alt.Chart(plot_file, title = product).mark_line().encode(
            x = alt.X('datetime:T'),
            y = alt.Y('final_price:Q'), color = alt.Color('brandasin')
            )

        chart_area.altair_chart(c.interactive(),use_container_width=True)
        columns = [col1,col2,col3,col4,col5,col6]
        for index, row in link_file.iterrows():
            columns[index].markdown(f"[{' : '.join([str(row['brand']),row['asin']])}]({row['link']})")
            columns[index].image(row['image'])
            try:
                columns[index].markdown(f"**:red[${row['final_price']:.2f}]**")
            except:
                columns[index].markdown(f"**:red[${row['final_price']}]**")
