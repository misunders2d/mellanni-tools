
import streamlit as st
import re
import plotly.graph_objects as go
from modules.keepa_modules import KeepaProduct, get_tokens

st.set_page_config(page_title = 'Sales estimator', page_icon = 'media/logo.ico',layout="wide")

import login_google
st.session_state['login']=login_google.login()
st.session_state['login']=(True, 'sergey@mellanni.com')


if st.session_state['login'][0]:
    tokens_left=get_tokens()
    st.subheader('_Get ASIN sales_')

    input_area=st.container()
    product_area=st.container()
    product_title_area, product_image_area=product_area.columns([3,1])
    plot_area=st.container()
    df_area=st.container()

    asin=input_area.text_input(f'ASIN ({tokens_left} tokens left)', key='ASIN', help='Enter ASIN or Amazon link to check latest stats. Currently available for US only')
    submit_button=input_area.button('Submit')
    
    def show_plot(df):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['sales min'],
                name='Sales min',
                mode='lines',
                yaxis='y1',
                line=dict(color='lightgrey')
                ))
        fig.add_trace(
            go.Scatter(x=df.index, y=df['sales max'],
                       name='Sales max',
                       mode='lines',
                       yaxis='y1',
                       fill='tonexty',
                       fillcolor='rgba(173, 216, 230, 0.3)',
                       line=dict(color='lightgrey')
                       ))

        fig.add_trace(go.Scatter(x=df.index, y=df['final price'], name='Final price', mode='lines', yaxis='y2',line=dict(color='red')))

        fig.add_trace(go.Scatter(x=df.index, y=df['BSR'], name='BSR', mode='lines', yaxis='y3',line=dict(color='lightgreen')))

        fig.update_layout(
            xaxis=dict(title='Months'),
            yaxis=dict(title='Sales min-max', side='left', showgrid=False),
            yaxis2=dict(title='Final price', side='right', overlaying='y', position=0.8, showgrid=False),
            yaxis3=dict(title='BSR', side='right', overlaying='y', anchor='free', position=0.9, showgrid=False)
        )
        plot_area.plotly_chart(fig, use_container_width=True)
        return

    if submit_button and asin:
        asin_clean=re.search('[A-Z0-9]{10}', asin).group()
        product=KeepaProduct(asin_clean.upper())
        try:
            product.generate_monthly_summary()
            product_title_area.write(product)
            if product.exists:
                product_title_area.write(f"View on Amazon: https://www.amazon.com/dp/{product.asin}")
                if product.image:
                    product_image_area.image(product.image)
                product.get_last_days(days=360)
                df_area.write('Latest price history and average sales per day:')
                df_area.dataframe(product.last_days)
                show_plot(product.summary)
        except Exception as e:
            st.write(e)