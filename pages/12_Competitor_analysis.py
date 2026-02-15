import os
import re

import streamlit as st
from google import genai
from google.genai import types
from openai import NotFoundError, OpenAI

from login import require_login
from modules.keepa_modules import get_product_details

st.set_page_config(
    page_title="Competitor analysis",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)


API_KEY = os.getenv("OPENAI_SUMMARIZER_KEY")
KEEPA_KEY = os.getenv("KEEPA_KEY")
HEIGHT = 250


require_login()


def generate_prompt(items, props):
    details = [types.Part(text = instructions)]
    product = ""
    for item in items:
        product += f"Product id: {item}\n"
        product += f'Product brand: {items[item].get("brand")}\n'
        if props.get("title", False):
            product += f'Product title: {items[item].get("title")}\n'
        if props.get("bullet", False):
            product += f'Product features: {items[item].get("bulletpoints")}\n'
        if props.get("description", False):
            product += f'Product description: {items[item].get("description")}\n'
        if props.get("price", False):
            product += f'Product price: {items[item].get("full price")}\n'
            product += f'Product discount: {items[item].get("discount")}\n'
        if props.get("sales", False):
            product += (
                f'Product sales per month: {items[item].get("monthly sales")} units\n\n'
            )
        if not props.get("image", False):
            details.append(types.Part(text = product))
        else:
            product += f'Product image: {items[item].get("image")}\n\n'
            details.append(types.Part( text = product))
            details.append(types.Part(
                    file_data = types.FileData(
                        file_uri = items[item].get("image"),
                        mime_type='image/jpg'))
            )
        product = ""
    return details


def compare_products(details, instructions, props, test=False):
    props_used = ", ".join([x for x in props if props[x] == True])  # type: ignore
    debug_area.write(
        f"The following props are used: {props_used}"
    )

    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"], vertexai=False)
    content = genai.types.Content( parts= details)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents = content
    )
    if (
        not response.candidates
        or not response.candidates[0].content
        or not response.candidates[0].content.parts
    ):
        return

    with response_area.chat_message("assistant", avatar="media/logo.ico"):
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            parts =response.candidates[0].content.parts
            for part in parts:
                if part.text:
                    st.write(part.text)
                    st.session_state.result += part.text
    return None


############# MAIN PAGE ##########################
try:
    with open("data/instructions.txt", "r") as instr:
        st.session_state.INSTRUCTIONS = instr.read()
except Exception as e:
    st.write(e)
if 'result' not in st.session_state:
    st.session_state['result'] = ''

header_area = st.empty()
debug_area = st.empty()
response_area = st.empty()
asin_col, props_col, instr_col = header_area.columns([2, 1, 5])

props_col.write("Attributes to use")
image_check = props_col.checkbox("Image", value=True, key="IMAGE")
title_check = props_col.checkbox("Title", value=True)
bullet_check = props_col.checkbox("Bulletpoints", value=False)
description_check = props_col.checkbox("Description", value=False)
price_check = props_col.checkbox("Price", value=True)
sales_check = props_col.checkbox("Monthly sales", value=True)
props_names = ["image", "title", "bullet", "description", "price", "sales"]
props_values = [
    image_check,
    title_check,
    bullet_check,
    description_check,
    price_check,
    sales_check,
]
props = {key: value for key, value in dict(zip(props_names, props_values)).items()}

if not image_check:
    st.warning("You deselected the image, please update your prompt accordingly!")
    st.session_state.INSTRUCTIONS = "Tell me about these products"

asins_input = asin_col.text_area(
    "Products",
    placeholder="Enter ASINs or Amazon.com links (up to 5 perferably)",
    height=HEIGHT,
)
instructions = instr_col.text_area(
    "Instructions (ask the bot anything about the products)",
    value=st.session_state.INSTRUCTIONS,
    height=HEIGHT,
)

if st.button("Analyze"):
    asins_str = re.split(" |,|\n|\t", asins_input)
    asins = []
    for asin in asins_str:
        asin_group = re.search("([A-Z0-9]{10})", asin)
        if asin_group:
            asins.append(asin_group.group().strip())

    if len(asins) == 0:
        st.error("No products to research")
    else:
        items = get_product_details(asins)
        details = generate_prompt(items, props)
        # st.write(details)
        try:
            compare_products(details, instructions, props, test=False)
        except NotFoundError as e:
            st.write(e)
        st.download_button(
            "Save results", data=st.session_state.result, file_name="results.md"
        )
