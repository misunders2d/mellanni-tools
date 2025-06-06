import os, re

from openai import OpenAI, NotFoundError
import base64, time
import streamlit as st
import keepa
from modules.keepa_modules import get_product_details



st.set_page_config(page_title = 'Competitor analysis', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state = 'collapsed')


API_KEY = os.getenv('OPENAI_SUMMARIZER_KEY')
KEEPA_KEY = os.getenv('KEEPA_KEY')
HEIGHT = 250

from login import login_st
if login_st():

    # def get_product_details(asins):
    #     api = keepa.Keepa(KEEPA_KEY)
    #     tokens = api.tokens_left
    #     if tokens < len(asins):
    #         st.write('Please wait, not enough tokens to pull data from Amazon')
    #         time.sleep(20)
    #     products = api.query(asins)
    #     items = {}
    #     for p in products:
    #         asin = p.get('asin')
    #         brand = p.get('brand')
    #         items[asin] = {}
    #         title = p.get('title')
    #         bulletpoints = p.get('features')
    #         description = p.get('description')
    #         price = p.get('data').get('df_NEW').dropna().iloc[-1].values[0]
    #         coupon = p.get('coupon')
    #         if not coupon:
    #             coupon = 0
    #         else:
    #             if coupon[0] < 0:
    #                 coupon = round(price * coupon[0] / 100,2)
    #             elif coupon[0] > 0:
    #                 coupon = -coupon[0]/100
                
    #         sales = p.get('monthlySold')
    #         if not sales:
    #             sales = 0
                
    #         img_link = 'https://m.media-amazon.com/images/I/' + p.get('imagesCSV').split(',')[0]
                
    #         items[asin]['brand'] = brand
    #         items[asin]['title'] = title
    #         items[asin]['bulletpoints'] = '\n'.join(bulletpoints)
    #         items[asin]['description'] = description
    #         items[asin]['full price'] = price
    #         items[asin]['discount'] = coupon
    #         items[asin]['monthly sales'] = sales
    #         items[asin]['image'] = img_link
    #     return items

    def generate_prompt(items, props):
        details = []
        product = ''
        for item in items:
            product += f'Product id: {item}\n'
            product += f'Product brand: {items[item].get("brand")}\n'
            if props.get('title',False):
                product += f'Product title: {items[item].get("title")}\n'
            if props.get('bullet', False):
                product += f'Product features: {items[item].get("bulletpoints")}\n'
            if props.get('description',False):
                product += f'Product description: {items[item].get("description")}\n'
            if props.get('price', False):
                product += f'Product price: {items[item].get("full price")}\n'
                product += f'Product discount: {items[item].get("discount")}\n'
            if props.get('sales', False):
                product += f'Product sales per month: {items[item].get("monthly sales")} units\n\n'
            if not props.get('image', False):
                details.append({'role':'user','content':product})
            else:
                product += f'Product image: {items[item].get("image")}\n\n'
                details.append({'role':'user','content':[
                    {'type':'text','text':product},
                    {"type": "image_url","image_url": {"url": items[item].get('image')}}
                    ]
                    })
            product = ''
        return details
        
    def compare_products(details, instructions, props, test = False):
        if test == True:
            props = {k:False for k in props}
        MODEL = "gpt-3.5-turbo-0125" if any([test == True, props.get('image',False) == False]) else "gpt-4o"
        MAX_TOKENS = 20 if test == True else 3000
        props_used = ', '.join([x for x in props if props[x] == True])# type: ignore
        debug_area.write(f'Using {MODEL} with {MAX_TOKENS} token limit. The following props are used: {props_used}')
        client = OpenAI(api_key=API_KEY)
        messages=[
            {"role": "system", "content": "You are an expert in Amazon product listings."},
            # {"role": "user", "content": "You are presented with images and price points of several products, along with their monthly sales. Please evaluate these products in terms of sellability, pointing out their weak and strong selling points"},
            {"role": "user", "content": instructions},
            ]
        messages.extend(details)
        if test == True:
            messages=[
                {"role": "system", "content": "You are an expert in Amazon product listings."},
                {"role": "user", "content": 'Once upon a time on Amazon...'}
                ]
        response = client.chat.completions.create(model = MODEL,messages = messages,max_tokens=MAX_TOKENS,stream = True)
        
        # if response.choices[0].finish_reason == 'stop':
        #     feedback = response.choices[0].message.content
        # else:
        #     feedback = response.choices[0].finish_reason
        # return feedback
        # saved_result = []
        # copy_result = response
        # for chunk in copy_result:
        #     if chunk.choices[0].delta.content is not None:
        #         saved_result.append(chunk.choices[0].delta.content)

        with response_area.chat_message('assistant', avatar = 'media/logo.ico'):
            st.session_state.result = st.write_stream(response)
        # st.session_state.result.write_stream(response)

        # for chunk in response:
        #     if chunk.choices[0].delta.content is not None:
        #         result.write_stream(chunk.choices[0].delta.content)
        return None



    ############# MAIN PAGE ##########################
    try:
        with open('data/instructions.txt','r') as instr:
            st.session_state.INSTRUCTIONS = instr.read()
    except Exception as e:
        st.write(e)

    header_area = st.empty()
    debug_area = st.empty()
    response_area = st.empty()
    asin_col, props_col, instr_col = header_area.columns([2,1,5])

    props_col.write('Attributes to use')
    image_check = props_col.checkbox('Image', value = True, key = 'IMAGE')
    title_check = props_col.checkbox('Title', value = True)
    bullet_check = props_col.checkbox('Bulletpoints', value = False)
    description_check = props_col.checkbox('Description', value = False)
    price_check = props_col.checkbox('Price', value = True)
    sales_check = props_col.checkbox('Monthly sales', value = True)
    props_names = ['image','title','bullet','description','price','sales']
    props_values = [image_check, title_check, bullet_check, description_check, price_check,sales_check]
    props = {key:value for key, value  in dict(zip(props_names, props_values)).items()}

    if image_check == False:
        st.warning('You deselected the image, please update your prompt accordingly!')
        st.session_state.INSTRUCTIONS = 'Tell me about these products'


    asins_input = asin_col.text_area('Products', placeholder='Enter ASINs or Amazon.com links (up to 5 perferably)', height=HEIGHT)
    instructions = instr_col.text_area('Instructions (ask the bot anything about the products)', value = st.session_state.INSTRUCTIONS, height=HEIGHT)

    if st.button('Analyze'):
        asins_str = re.split(' |,|\n|\t', asins_input)
        asins =  [re.search('([A-Z0-9]{10})', x).group().strip() for x in asins_str if re.search('([A-Z0-9]{10})', x)]
        if len(asins) == 0:
            st.error('No products to research')
        else:
            items = get_product_details(asins)
            details = generate_prompt(items, props)
            # st.write(details)
            try:
                compare_products(details, instructions, props, test = False)
            except NotFoundError as e:
                st.write(e)
            st.download_button('Save results', data = st.session_state.result, file_name = 'results.md')

