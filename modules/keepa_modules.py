import keepa
import os
import streamlit as st
import time

KEEPA_KEY = os.getenv('KEEPA_KEY')


def get_product_details(asins: list[str]):
    api = keepa.Keepa(KEEPA_KEY)
    tokens = api.tokens_left
    if tokens < len(asins):
        st.write('Please wait, not enough tokens to pull data from Amazon')
        time.sleep(20)
    products = api.query(asins)
    items = {}
    for p in products:
        asin = p.get('asin')
        brand = p.get('brand')
        items[asin] = {}
        title = p.get('title')
        bulletpoints = p.get('features')
        description = p.get('description')
        price = p.get('data').get('df_NEW').dropna().iloc[-1].values[0]
        coupon = p.get('coupon')
        if not coupon:
            coupon = 0
        else:
            if coupon[0] < 0:
                coupon = round(price * coupon[0] / 100,2)
            elif coupon[0] > 0:
                coupon = -coupon[0]/100
            
        sales = p.get('monthlySold')
        if not sales:
            sales = 0
            
        img_link = 'https://m.media-amazon.com/images/I/' + p.get('imagesCSV').split(',')[0]
            
        items[asin]['brand'] = brand
        items[asin]['title'] = title
        items[asin]['bulletpoints'] = '\n'.join(bulletpoints)
        items[asin]['description'] = description
        items[asin]['full price'] = price
        items[asin]['discount'] = coupon
        items[asin]['monthly sales'] = sales
        items[asin]['image'] = img_link
    return items
