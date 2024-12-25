
import streamlit as st
import re
import pandas as pd

from modules.keepa_modules import KeepaProduct, get_tokens

import login_google
st.session_state['login'] = login_google.login()
# st.session_state['login'] = (True, 'sergey@mellanni.com')


if st.session_state['login'][0]:
    tokens_left = get_tokens()
    st.subheader('_Get ASIN sales_')

    input_area = st.container()
    product_area = st.container()
    product_title_area, product_image_area = product_area.columns([3,1])
    df_area = st.container()
    plot_area = st.container()

    asin = input_area.text_input(f'ASIN ({tokens_left} tokens left)', max_chars=10, key = 'ASIN', help='Enter ASIN or Amazon link to check latest stats. Currently available for US only')
    submit_button = input_area.button('Submit')
    if submit_button and asin:
        asin_clean = re.search('[A-Z0-9]{10}', asin).group()
        product = KeepaProduct(asin_clean)
        try:
            product.generate_daily_sales()
            product_title_area.write(product)
            product_title_area.write(f"View on Amazon: https://www.amazon.com/dp/{product.asin}")
            if product.image:
                product_image_area.image(product.image)
            product.get_last_days(days=360)
            df_area.write('Latest price history and average sales per day:')
            df_area.dataframe(product.last_days)
        except Exception as e:
            st.write(e)