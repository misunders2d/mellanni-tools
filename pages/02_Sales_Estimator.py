
import streamlit as st
import re
import plotly.graph_objects as go
import pandas as pd
# from modules import keepa_modules
from modules.keepa_modules import KeepaProduct, get_tokens, get_products

st.set_page_config(page_title = 'Sales estimator', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')

import login_google
st.session_state['login']=login_google.login()
# st.session_state['login']=(True, 'sergey@mellanni.com')


if st.session_state['login'][0]:
    tokens_left=get_tokens()
    st.subheader('_Get ASIN sales_')

    indivudual, bulk = st.tabs(['Sales Estimator', 'Bulk ASIN processing'])

    ##### INDIVIDUAL SECTION #####

    input_area=indivudual.container()
    text_col, market_col = input_area.columns([4,1])
    plot_container=indivudual.container()
    plot_area, selector_area = plot_container.columns([5,1])
    plot_selection = selector_area.radio('Select plot type',['Monthly','Daily','Keepa'], disabled=False, index=2)
    plot_last_days = selector_area.number_input('Enter # of days to show the plot for', min_value=1, max_value=3600, value=30, step=1)
    include_variations = selector_area.checkbox('Include variations', value=False, help='Check to calculate sales and price for all variations')


    product_area=indivudual.container()
    product_title_area, product_image_area=product_area.columns([10,1])
    variations_area = indivudual.container()
    variations_info, variations_image = variations_area.columns([10,1])
    df_area=indivudual.container()
    df_history, df_variations = df_area.columns([5,5])

    def calculate_variation_sales(product:KeepaProduct, days=plot_last_days, market="US"):
        
        asins = list(product.variations)
        products_data = get_products(asins)
        
        products = [KeepaProduct(asin, domain=market) for asin in asins]
        for ap in products:
            ap.extract_from_products(products_data)
            ap.get_last_days(days)
            ap.get_variations()
        
        variations_df = pd.DataFrame()
        min_price = 100000
        max_price = 0
        min_sales = 0
        max_sales = 0
        min_dollar_sales = 0
        max_dollar_sales = 0
        revenue = 0
        for ap in products:
            if ap.full_price > max_price:
                max_price = ap.full_price
            if ap.full_price < min_price:
                min_price = ap.full_price

            min_sales += ap.min_sales
            max_sales += ap.max_sales
            min_dollar_sales += (ap.min_sales * ap.avg_price)
            max_dollar_sales += (ap.max_sales * ap.avg_price)
            revenue += ap.avg_sales * ap.avg_price
            temp_df = pd.DataFrame({'ASIN':ap.asin, 'Brand':ap.brand, 'Sales min':ap.min_sales, 'Sales max':ap.max_sales, 'Avg price':round(ap.avg_price,2)}, index=[0])
            for key, value in ap.variation_theme.items():
                temp_df[key] = value
            variations_df = pd.concat([variations_df, temp_df])
        variations_df.set_index('ASIN', inplace=True)
        variations_df.sort_values(by='Sales max', ascending=False, inplace=True)
        real_prices = variations_df['Avg price'].min(), variations_df['Avg price'].max()
        std_prices = min_price, max_price
        return int(min_sales), int(max_sales), round(min_dollar_sales / min_sales,2), max(products), min(products), revenue, variations_df, real_prices, std_prices

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
        
        # if type=='Monthly':
        #     plot_title = 'Months'
        # elif type == "Daily":
        #     plot_title = 'Days'
        # else:
        #     plot_title = 'Minutes'

        fig.update_layout(
            # xaxis=dict(title=plot_title),
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

    asin=text_col.text_input(f'ASIN ({tokens_left} tokens left)', key='ASIN', help='Enter ASIN (all caps) or Amazon link to check latest stats. Currently available for US only')
    market=market_col.radio('Select market (experimental)', ['US', 'GB', 'FR'], index=0, horizontal=True) #['US', 'UK', 'DE', 'FR', 'IT', 'ES', 'JP']
    submit_button=input_area.button('Submit', icon=':material/local_fire_department:')

    if submit_button and len(asin)>=10:
        try:
            asin_clean=re.search('[A-Z0-9]{10}', asin.upper()).group() if len(asin)>10 else asin.upper()
        except Exception:
            indivudual.warning('Wrong ASIN combination')
        product=KeepaProduct(asin_clean.upper(), domain=market)
        product.initial_days = plot_last_days
        try:
            product.generate_monthly_summary()
        except Exception as e:
            indivudual.write(e)
        if product:
            product_title_area.markdown('### ASIN result:')
            for chunk in product.__str__(days=plot_last_days).split('\n'):
                product_title_area.markdown(chunk)
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
                    try:
                        if product.variations and (len(product.variations) < (tokens_left*0.8)):
                            min_sales, max_sales, avg_price, bestseller, worstseller, revenue, variations_df, real_prices, std_prices = calculate_variation_sales(product, market=market)
                            variations_str = f"Total sales for all variations: {min_sales:,.0f} - {max_sales:,.0f} (**{(min_sales + max_sales)/2:,.0f}** average) last {plot_last_days} days\
                                \nAverage price: **\${avg_price}** (**\${revenue:,.0f}** total revenue)\
                                \nReal price range: \${real_prices[0]:.2f} - \${real_prices[1]:.2f}\
                                \nStandard prices: \${std_prices[0]:.2f} - \${std_prices[1]:.2f}"
                            bestseller_str = f"Bestseller: {bestseller.__str__(days=plot_last_days)}"
                            ### render variations and bestseller
                            variations_info.markdown('### Parent results:')
                            for chunk in variations_str.split('\n'):
                                variations_info.markdown(chunk)
                            variations_info.markdown('### Bestseller:')
                            for chunk in bestseller_str.split('\n'):
                                variations_info.markdown(chunk)
                            variations_info.write(f"View Bestseller on Amazon: https://www.amazon.com/dp/{bestseller.asin}")
                            if bestseller.image:
                                variations_image.image(bestseller.image, caption=bestseller.asin)
                            variations_info.divider()
                            
                            
                            df_variations.write('Variations performance')
                            df_variations.dataframe(variations_df)
                        elif product.variations and len(product.variations) > (tokens_left*0.8):
                            indivudual.warning(f'Too many variations to calculate, not enough tokens. Please uncheck "Include variations"')
                        elif not product.variations:
                            indivudual.warning('No variations found')
                            df_variations.write('Variations performance')
                            product_df = pd.DataFrame({'ASIN':product.asin, 'Brand':product.brand, 'Sales min':product.min_sales, 'Sales max':product.max_sales, 'Avg price':round(product.avg_price,2)}, index=[0])
                            product_df.set_index('ASIN', inplace=True)
                            df_variations.dataframe(product_df)
                    except Exception as e:
                        indivudual.warning(f'Sorry, error occurred.\n{e}')

    #### BULK SECTION #####
    bulk_input_area = bulk.container()
    bulk_button_area = bulk.container()

    def bulk_update_asins():
       st.session_state['bulk_asins'] = st.session_state['bulk_asin_input']
    #    st.write(st.session_state['bulk_asins']) 

    bulk_asin_input = bulk_input_area.text_area(
        'Enter ASINs (one per line)',
        height=200,
        key='bulk_asin_input',
        on_change=bulk_update_asins,
        placeholder=f'You have {tokens_left} tokens remaining')
    bulk_btn_col, bulk_vars_col, bulk_days_col = bulk_button_area.columns([4,3,1], vertical_alignment='center')
    include_bulk_variations = bulk_vars_col.checkbox('Include all variations?')
    bulk_days = bulk_days_col.number_input('# of days to cover', min_value=1, max_value=360, value=90, step=1)
    if bulk_btn_col.button('Submit', key='bulk_button', help='Submit ASINs for processing'):
        if bulk_asin_input:
            try:
                bulk_df = pd.DataFrame()
                asins_bulk = re.split(r'[\n\r,]', bulk_asin_input)
                asins_bulk = [re.search('B[A-Z0-9]{9}', asin.upper()).group() for asin in asins_bulk]
                products = [KeepaProduct(asin, domain="US") for asin in asins_bulk]
                products_data = get_products(asins_bulk)
                if include_bulk_variations:
                    bulk_variations = set()
                    for p in products:
                        p.get_variations()
                        bulk_variations.update(p.variations)
                    variations_data = get_products(list(bulk_variations))
                    products_data.extend(variations_data)
                    asins_bulk.extend(list(bulk_variations))
                    products = [KeepaProduct(asin, domain="US") for asin in asins_bulk]
                for ap in products:
                    ap.extract_from_products(products_data)
                    ap.get_last_days(days=bulk_days)
                    ap.get_variations()
                    images = ap.data[0].get('imagesCSV','').split(',')
                    main_image = '=HYPERLINK("https://m.media-amazon.com/images/I/' + images[0] + '")'
                    df_data = {
                        'asin':[ap.asin],
                        'parent':[ap.data[0].get('parentAsin')],
                        'brand':[ap.brand],
                        'sales_min':[ap.min_sales],
                        'sales_max':[ap.max_sales],
                        'average_price':[ap.avg_price],
                        'full_price':[ap.full_price],
                        'image':[main_image]
                        }
                    if 'variation_theme' in ap.__dict__:
                        variation_theme = {theme:[value] for theme, value in ap.variation_theme.items()}
                        df_data.update(variation_theme)
                    temp=pd.DataFrame(df_data)
                    bulk_df = pd.concat([bulk_df, temp])

                bulk.dataframe(bulk_df, use_container_width=True, hide_index=True)
            except Exception as e:
                bulk.warning(f'Sorry, error occurred.\n{e}')