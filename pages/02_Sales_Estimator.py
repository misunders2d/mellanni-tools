
import streamlit as st
import re
import plotly.graph_objects as go
import pandas as pd
from modules import keepa_modules
from modules.keepa_modules import KeepaProduct, get_tokens, get_products

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
    plot_selection = selector_area.radio('Select plot type',['Monthly','Daily','Keepa'], disabled=False)
    plot_last_days = selector_area.number_input('Enter # of days to show the plot for', min_value=1, max_value=3600, value=360, step=1)
    include_variations = selector_area.checkbox('Include variations', value=False, help='Check to calculate sales and price for all variations')


    product_area=st.container()
    product_title_area, product_image_area=product_area.columns([10,1])
    variations_area = st.container()
    variations_info, variations_image = variations_area.columns([10,1])
    df_area=st.container()
    df_history, df_variations = df_area.columns([5,5])

    def calculate_variation_sales(product:KeepaProduct):
        
        asins = list(product.variations)
        products_data = get_products(asins)
        
        products = [KeepaProduct(asin) for asin in asins]
        for ap in products:
            ap.extract_from_products(products_data)
            ap.get_last_days(30)
        
        variations_df = pd.DataFrame(columns=['ASIN','Sales min','Sales max','Avg price'])
        min_sales = 0
        max_sales = 0
        min_dollar_sales = 0
        max_dollar_sales = 0
        for ap in products:
            ap.get_last_days(30)
            min_sales += ap.min_sales
            max_sales += ap.max_sales
            min_dollar_sales += (ap.min_sales * ap.avg_price)
            max_dollar_sales += (ap.max_sales * ap.avg_price)
            temp_df = pd.DataFrame({'ASIN':ap.asin, 'Sales min':ap.min_sales, 'Sales max':ap.max_sales, 'Avg price':ap.avg_price}, index=[0])
            variations_df = pd.concat([variations_df, temp_df])
        variations_df.set_index('ASIN', inplace=True)
        variations_df.sort_values(by='Sales max', ascending=False, inplace=True)
        return int(min_sales), int(max_sales), round(min_dollar_sales / min_sales,2), max(products), min(products), variations_df

    def show_plot(df, type='Monthly'):
        price_col = 'full price' if type=='Keepa' else 'final price'
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
            yaxis=dict(title='Sales min-max', side='left', showgrid=False, range=[0, max(2,max(df['sales max'])*1.01)]),
            yaxis2=dict(
                title='Final price', side='left', overlaying='y', position=0.05,
                showgrid=False, range=[0, max(df['final price'])*1.1],
                titlefont=dict(color='red'),
                tickfont=dict(color='red')
                ),
            yaxis3=dict(
                title='BSR', side='right', overlaying='y', anchor='free', position=1,
                showgrid=False, range=[1, max(1000, max(df['BSR']))],
                titlefont=dict(color='lightgreen'),
                tickfont=dict(color='lightgreen')
                )
        )
        return fig

    asin=input_area.text_input(f'ASIN ({tokens_left} tokens left)', key='ASIN', help='Enter ASIN (all caps) or Amazon link to check latest stats. Currently available for US only')
    
    submit_button=input_area.button('Submit', icon=':material/local_fire_department:')

    if submit_button and len(asin)>=10:
        try:
            asin_clean=re.search('[A-Z0-9]{10}', asin.upper()).group() if len(asin)>10 else asin.upper()
        except Exception:
            st.warning('Wrong ASIN combination')
        product=KeepaProduct(asin_clean.upper())
        product.initial_days = plot_last_days
        try:
            product.generate_monthly_summary()
        except Exception as e:
            st.write(e)
        if product:
            product_title_area.markdown(f'### ASIN result:\n{product}')
            if product.exists:
                product_title_area.write(f"View on Amazon: https://www.amazon.com/dp/{asin}")
                if product.image:
                    product_image_area.image(product.image, caption=product.asin)
                product.get_last_days(days=int(plot_last_days))
                df_history.write('Latest price history and average sales per day:')
                df_history.dataframe(product.last_days)
                if plot_selection=='Monthly':
                    fig = show_plot(product.summary, type=plot_selection)
                elif plot_selection=='Keepa':
                    fig = show_plot(product.short_history, type=plot_selection)
                elif plot_selection=='Daily':
                    fig = show_plot(product.last_days, type=plot_selection)
                plot_area.plotly_chart(fig, use_container_width=True)
                product_title_area.divider()

                if include_variations:
                    product.get_variations()
                    if product.variations and len(product.variations) < (tokens_left*0.8):
                        min_sales, max_sales, avg_price, bestseller, worstseller, variations_df = calculate_variation_sales(product)
                        variations_str = f"Total sales for all variations: {min_sales:,.0f} - {max_sales:,.0f} per month, average price: ${avg_price}"
                        bestseller_str = f"Bestseller: {bestseller}"
                        variations_info.markdown(f'### Parent results:\n{variations_str}\n### Bestseller - {bestseller}')
                        variations_info.write(f"View Bestseller on Amazon: https://www.amazon.com/dp/{bestseller.asin}")
                        if bestseller.image:
                            variations_image.image(bestseller.image, caption=bestseller.asin)
                        variations_info.divider()
                        df_variations.write('Variations performance')
                        df_variations.dataframe(variations_df)
                    elif len(product.variations) > (tokens_left*0.8):
                        st.warning(f'Too many variations to calculate, not enough tokens. Please uncheck "Include variations"')
