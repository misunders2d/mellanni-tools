
import streamlit as st
import re
import plotly.graph_objects as go
from modules.keepa_modules import KeepaProduct, get_tokens

st.set_page_config(page_title = 'Sales estimator', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')

import login_google
st.session_state['login']=login_google.login()
# st.session_state['login']=(True, 'sergey@mellanni.com')


if st.session_state['login'][0]:
    tokens_left=get_tokens()
    st.subheader('_Get ASIN sales_')

    input_area=st.container()
    plot_container=st.container()
    plot_area, selector_area = plot_container.columns([5,1])
    plot_selection = selector_area.radio('Select plot type',['Monthly','Keepa'], disabled=False)
    product_area=st.container()
    product_title_area, product_image_area=product_area.columns([3,1])
    df_area=st.container()

    def show_plot(df, type='Monthly'):
        price_col = 'final price' if type=='Monthly' else 'full price'
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

        fig.add_trace(go.Scatter(x=df.index, y=df[price_col], name='Price', mode='lines', yaxis='y2',line=dict(color='red')))
        if type=='Keepa':
            fig.add_trace(go.Scatter(x=df.index, y=df['LD'], name='Lightning Deal', mode='lines+markers', yaxis='y2',line=dict(color='pink'), marker=dict(symbol='circle')))
            fig.add_trace(go.Scatter(x=df.index, y=df['coupon'], name='Coupon', mode='lines', yaxis='y2',line=dict(color='green')))


        fig.add_trace(go.Scatter(x=df.index, y=df['BSR'], name='BSR', mode='lines', yaxis='y3',line=dict(color='lightgreen')))

        fig.update_layout(
            xaxis=dict(title='Months') if type=='Monthly' else dict(title='Hour'),
            yaxis=dict(title='Sales min-max', side='left', showgrid=False, range=[0, max(10,max(df['sales max'])*1.01)]),
            yaxis2=dict(
                title='Final price', side='left', overlaying='y', position=0.05,
                showgrid=False, range=[0, max(df['final price'])*1.3],
                titlefont=dict(color='red'), tickfont=dict(color='red')
                ),
            yaxis3=dict(
                title='BSR', side='right', overlaying='y', anchor='free', position=1,
                showgrid=False, range=[1, 1000, max(100000, max(df['BSR'])*1.01)],
                titlefont=dict(color='lightgreen'), tickfont=dict(color='lightgreen')
                )
        )
        return fig

    st.session_state.asin=input_area.text_input(f'ASIN ({tokens_left} tokens left)', key='ASIN', help='Enter ASIN (all caps) or Amazon link to check latest stats. Currently available for US only')
    
    submit_button=input_area.button('Submit', icon=':material/local_fire_department:')

    if submit_button and len(st.session_state.asin)>=10:
        st.session_state.asin_clean=re.search('[A-Z0-9]{10}', st.session_state.asin).group() if len(st.session_state.asin)>10 else st.session_state.asin
        st.session_state.product=KeepaProduct(st.session_state.asin_clean.upper())
        try:
            st.session_state.product.generate_monthly_summary()
        except Exception as e:
            st.write(e)
    if 'product' in st.session_state:
        product_title_area.write(st.session_state.product)
        if st.session_state.product.exists:
            product_title_area.write(f"View on Amazon: https://www.amazon.com/dp/{st.session_state.asin}")
            if st.session_state.product.image:
                product_image_area.image(st.session_state.product.image)
            st.session_state.product.get_last_days(days=360)
            df_area.write('Latest price history and average sales per day:')
            df_area.dataframe(st.session_state.product.last_days)
            if plot_selection=='Monthly':
                fig = show_plot(st.session_state.product.summary, type=plot_selection)
            elif plot_selection=='Keepa':
                fig = show_plot(st.session_state.product.short_history, type=plot_selection)
            plot_area.plotly_chart(fig, use_container_width=True)

