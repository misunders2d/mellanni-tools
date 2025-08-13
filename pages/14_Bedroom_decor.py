from openai import OpenAI
import base64, time, json
import streamlit as st
from streamlit.runtime import scriptrunner
from PIL import Image, ImageOps
from io import BytesIO
from random import randint
import threading
import requests
import os
import pandas as pd
from datetime import date, timedelta

from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(
    page_title="Bedroom designer",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)


API_KEY = os.getenv("OPENAI_SUMMARIZER_KEY")
KEEPA_KEY = os.getenv("KEEPA_KEY")
SD_TOKEN = os.getenv("SD_KEY")
HEIGHT = 250
NUM_OPTIONS = "two to three"  #'two to three' 'one'
STYLE = "vivid"  # ,'vivid', 'natural'
IMG_SIZE: str = "1024x1024"
VISION_MODEL = "gpt-4-turbo-2024-04-09"  # "gpt-4-vision-preview" "gpt-4-turbo-2024-04-09" - new version
st.session_state.DONE = False
if "IMAGES" not in st.session_state:
    st.session_state.IMAGES = {"full": [], "edit": []}
collections_mapping = {
    "pillowcases": ["1800 Pillowcase Set 2 pc", "1800 Pillowcase Set 4 pc"],
    "flat sheet": ["1800 Flat Sheet"],
    "fitted sheet": ["1800 Fitted Sheet"],
    "bed skirt": ["1800 Bedskirt"],
    "coverlet": ["1800 Ultrasonic Coverlet"],
}

JSON_EXAMPLE = {
    "option 1": {
        "pillowcase": "pillowcase color",
        "flat sheet": "flat sheet color",
        "fitted sheet": "fitted sheet color",
        "bed skirt": "bed skirt color (only if it exists in the original image)",
        "coverlet": "coverlet color (if any)",
        "prompt": "description WITH UPDATED BEDDING ITEMS' COLORS AND ADDITIONAL ITEMS, IF APPLICABLE",
    },
    "option 2": {
        "pillowcase": "pillowcase color",
        "flat sheet": "flat sheet color",
        "fitted sheet": "fitted sheet color",
        "bed skirt": "bed skirt color (only if it exists in the original image)",
        "coverlet": "coverlet color (if any)",
        "prompt": "description WITH UPDATED BEDDING ITEMS' COLORS AND ADDITIONAL ITEMS, IF APPLICABLE",
    },
}

JSON_EXAMPLE_SD = {
    "option 1": {
        "bed": "style and material of the bed",
        "pillowcase": "pillowcase color",
        "flat sheet": "flat sheet color",
        "fitted sheet": "fitted sheet color",
        "bed skirt": "bed skirt color (only if it exists in the original image)",
        "coverlet": "coverlet color (if any)",
        # "prompt":"description WITH UPDATED BEDDING ITEMS' COLORS AND ADDITIONAL ITEMS, IF APPLICABLE"
    },
    "option 2": {
        "bed": "style and material of the bed",
        "pillowcase": "pillowcase color",
        "flat sheet": "flat sheet color",
        "fitted sheet": "fitted sheet color",
        "bed skirt": "bed skirt color (only if it exists in the original image)",
        "coverlet": "coverlet color (if any)",
        # "prompt":"description WITH UPDATED BEDDING ITEMS' COLORS AND ADDITIONAL ITEMS, IF APPLICABLE"
    },
}


ERROR_JSON = {"error": "this is not an image of a bedroom"}

input_tokens = 0
output_tokens = 0


@st.cache_resource(show_spinner=False)
def get_stock():
    GC_CREDENTIALS = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = bigquery.Client(credentials=GC_CREDENTIALS)
    query = f"""
                SELECT date, sku, asin, afn_fulfillable_quantity
                FROM `reports.fba_inventory`
                WHERE DATE(date) >= DATE("{(date.today()-timedelta(days = 2)).strftime('%Y-%m-%d')}")
                AND country_code = "US"
                AND condition = "New"
                """
    inventory = client.query(query).result().to_dataframe()
    inventory = inventory[inventory["date"] == inventory["date"].max()]
    inventory = (
        inventory.groupby("asin")["afn_fulfillable_quantity"].sum().reset_index()
    )
    inventory = inventory[inventory["afn_fulfillable_quantity"] > 0]
    collections = '", "'.join(
        [
            "1800 Bedskirt",
            "1800 Fitted Sheet",
            "1800 Flat Sheet",
            "1800 Pillowcase Set 2 pc",
            "1800 Pillowcase Set 4 pc",
            "1800 Ultrasonic Coverlet",
        ]
    )
    query = f"""SELECT asin, collection, size, color, pattern, pantone_number
                FROM `auxillary_development.dictionary`
                WHERE collection IN("{collections}")"""
    dictionary = client.query(query).result().to_dataframe()
    stock = pd.merge(dictionary, inventory, how="right", on="asin")
    stock = stock.dropna(subset="collection")
    stock = stock[~stock["color"].str.lower().str.contains("hydrengea")]
    stock["pattern"] = (
        stock["pattern"]
        .str.replace("True".lower(), "True")
        .str.replace("False".lower(), "False")
    )
    stock = stock[stock["pattern"] == "False"]
    return stock


@st.cache_resource(show_spinner=False)
def get_colors(stock):
    colors = {}
    for alias, collection in collections_mapping.items():
        colors[alias] = ", ".join(
            stock[stock["collection"].isin(collection)]["color"].unique().tolist()
        )
    return colors


def match_pantones(colors: list, stock: pd.DataFrame) -> dict:
    colors = [color.upper() for color in colors]
    stock["color"] = stock["color"].str.upper()
    stock = stock[stock["color"].isin(colors)]
    pantones = (
        stock.drop_duplicates("color")[["color", "pantone_number"]]
        .set_index("color")
        .to_dict(orient="index")
    )
    pantones = {k: v["pantone_number"] for k, v in pantones.items()}
    return pantones


def match_color(alias, color, df):
    df["color"] = (
        df["color"]
        .str.lower()
        .str.replace("-", " ")
        .str.replace("/", " ")
        .str.replace("  ", " ")
        .str.replace("\\", " ")
        .str.strip()
    )
    color = (
        color.lower()
        .replace("-", " ")
        .replace("/", " ")
        .replace("  ", " ")
        .replace("\\", " ")
        .strip()
    )
    df = df[
        (df["collection"].isin(collections_mapping[alias])) & (df["color"] == color)
    ]
    if len(df) > 0:
        df = df.sort_values("afn_fulfillable_quantity", ascending=False)
        asin = df.loc[:, "asin"].values[0]
    else:
        asin = "Not_found"
    return asin


st.session_state.stock = get_stock()
st.session_state.colors = get_colors(st.session_state.stock)

COLOR_STR = ""
for k, v in st.session_state.colors.items():
    COLOR_STR += k + ": " + v + ",\n\n"
COLOR_PROMPT = f"Please choose ONLY from these available colors: {COLOR_STR}"

PROMPT_OLD = f"""You are supplied with an image of a bedroom.
As a bedding designer and expert please suggest the best color combinations of bedding items for this specific bedroom interior and layout - a set of pillowcases, flat sheet, fitted sheet,
bedskirt (if applicable) and a coverlet (if applicable).
Keep in mind the color of walls, ceiling, floor, the bed itself, any furniture and wall decorations, if any.
Please choose {NUM_OPTIONS} best options and describe them in detail as if you were generating prompts for an image-genearting model.
When describing, please try to stay as close to the original image, as possible - the ONLY thing that needs to be changed is the color of bedding items.
IMPORTANT: Keep the number of items (especially pillowcases) intact. Keep the view angle the same as in the original image. Keep the interior and decor the same.
DO NOT ADD EXTRA PILLOWS OR PILLOWCASES.
Please explicitly name the color of each bedding item in your prompt.
Return your response STRICTLY in json format, like this:
{JSON_EXAMPLE}
and so on, where values for "pillowcase", "flat sheet", "fitted sheet", "bed skirt" and "coverlet" are their respective colors from your suggestion. Do not add anything from yourself.
If the image supplied does not appear to be an image of a bedroom, please return the following JSON response:
{ERROR_JSON}"""

PROMPT_SD = f"""You are a bedding styling and design expert.
You are supplied with an an image of a bedroom.
Please note all the bedding items on the bed and suggest EXACTLY {NUM_OPTIONS} best color combinations of bedding items for this type and style of interior.
Return your response STRICTLY in json format, like this:
{JSON_EXAMPLE_SD}
and so on, where values for "pillowcase", "flat sheet", "fitted sheet", "bed skirt" and "coverlet" are their respective colors that you suggest,
value for "bed" is the type, material and style of the bed itself.
Besides the json response do not add anything from yourself.
"""

PROMPT = f"""You are a bedding design expert and an expert in photoshooting.
Below is an image of a bedroom.
Note the bedroom interior in detail and relative positions of items on the image,
color and material of walls, ceiling, floor and anything visible in the picture.
Also note full details of the bed - the material and color of which it is made.
DISREGARD THE COLOR OF everything that's on the bed - sheets, pillowcases, bed skirt, coverlets etc, specifically record the number of pillows.
Then, based on the current details, please come up with EXACTLY {NUM_OPTIONS} best suggestions of color designs for all bedding items that you see,
make sure to explicitly include pillowcases, flat sheet, fitted sheet.
DO NOT suggest a bedskirt if it's not on the on the original photo.
If there is a coverlet on the original photo, add coverlet suggestions.
Describe the "improved" bedding using the same interior and bed details you noted before, explicitly mentioning the colors of all bedding items.
Make sure to capitalize all bedding items and their color names.
Stay detail-focused, do not add anything emotional or whimsical.
Make sure to shape your description so that it implies creating a photorealistic image based on it.

Return your response STRICTLY in json format, like this:
{JSON_EXAMPLE}
and so on, where values for "pillowcase", "flat sheet", "fitted sheet", "bed skirt" and "coverlet" are their respective colors that you suggest,
and values for "prompt" is the description you generated, where the description remains unchanged except for the color of bedding items you suggest, and additional coverlet or bed skirt if you are suggesting them and they were absent on the original photo.
MAKE SURE TO CHANGE THE COLOR OF THE ITEMS in each of your descriptions according to your design suggestions and add bed skirt and/or coverlet if you are suggesting them.
Do not change anything else in your description.
Besides the json response do not add anything from yourself."""
# In case you cannot identify a bed and bedding on the supplied image, please return the following JSON response:
# {ERROR_JSON}
# """
PROMPT_TEST: str = f"""You are a bedding design expert and you are supplied with an image of a bedroom.
Please take a careful look at this image, note the bedroom interior and suggest {NUM_OPTIONS} bedding improvements,
specifically colors for pillowcases, flat sheet, fitted sheet, bed skirt and coverlet, based on your expertise and aesthetic compatibility with the interior.
Return your response STRICTLY in json format, like this:
{JSON_EXAMPLE}
and so on, where values for "pillowcase", "flat sheet", "fitted sheet", "bed skirt" and "coverlet" are their respective colors from your suggestion. Do not add anything from yourself.
"""


def resize_image(image_obj):
    full_image = Image.open(image_obj)
    cropped_image = ImageOps.contain(full_image, (512, 512))
    return cropped_image


def convert_image_to_bytes(image_obj):
    img_byte_arr = BytesIO()
    image_obj.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr


def encode_image(image_path):
    if isinstance(image_path, str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    elif isinstance(image_path, bytes):
        return base64.b64encode(image_path).decode("utf-8")


def describe_image(image_bytes):
    prompt_to_use = PROMPT if mode == "Full revision" else PROMPT_SD
    global input_tokens, output_tokens
    time.sleep(randint(30, 70) / 10)

    message: list = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_to_use},
                {"type": "text", "text": COLOR_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_bytes}",
                        "detail": "high",
                    },
                },
            ],
        }
    ]

    client = OpenAI(api_key=API_KEY)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=message,
        max_tokens=1500,
        temperature=0.0,
        n=1,
        stream=False,
    )

    stop = response.choices[0].finish_reason

    if stop == "stop":
        description = response.choices[0].message.content
    else:
        st.write(stop)
        description = '{"error":"There was an error, please try again."}'
    input_tokens += response.usage.prompt_tokens
    output_tokens += response.usage.completion_tokens
    try:
        description = json.loads(description.replace("```", "").replace("json\n", ""))
    except:
        description = {"error": "There was an error, please try again."}
    return description


def sd_edit(bytes_image, version):
    # option = options[version]
    option = {item: color.upper() for item, color in version.items()}
    PANTONE_DICT = match_pantones(option.values(), st.session_state.stock)
    pantone_match = {
        item: value + " (" + PANTONE_DICT.get(value, value) + ")"
        for item, value in option.items()
        if item != "bed" and value != "NOT APPLICABLE"
    }

    # bedding = ', '.join(["("+str(value) + ":0.9)" + " " + str(key) for key, value in pantone_match.items()])
    bedding = ", ".join(
        [str(value) + " " + str(key) for key, value in pantone_match.items()]
    )
    negative_bedding = ", ".join(
        [key + " of any other color than " + value for key, value in option.items()]
    )

    prompt = f"""A {option.get('bed')} bed, with the following bedding items with respective Pantone color numbers: {bedding}""".replace(
        "pillowcase", "pillowcases"
    )
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/edit/search-and-replace",
        headers={"authorization": f"Bearer {SD_TOKEN}", "accept": "image/*"},
        files={"image": bytes_image},
        data={
            "prompt": prompt,
            "search_prompt": "bed with bed sheets and bedding items",
            "output_format": "jpeg",
            "negative_prompt": negative_bedding + ", prints or patterns on the bedding",
        },
    )

    if response.status_code == 200:
        option["url"] = Image.open(BytesIO(response.content))
        option["revised_prompt"] = prompt
        st.session_state.IMAGES["edit"].append(option)
    else:
        raise Exception(str(response.json()))


def generate_image(full_prompt):
    PANTONE_DICT = match_pantones(full_prompt.values(), st.session_state.stock)
    pantone_match = {
        item: PANTONE_DICT.get(value, value) for item, value in full_prompt.items()
    }
    include_items = {
        "ONE " + item.upper(): value
        for item, value in pantone_match.items()
        if "None" not in value
    }
    ITEMS = ", ".join([item for item in include_items])
    ITEMS = ITEMS.replace("PILLOWCASE", "TWO PILLOWCASES")
    ITEMS_STR = ""
    for item, color in include_items.items():
        ITEMS_STR += item + ": " + color + ", "
    ITEMS_STR = ITEMS_STR.replace("PILLOWCASE", "PILLOWCASES")

    prompt = (
        """
My prompt has full detail so no need to add more. DO NOT REWRITE OR MODIFY THE ORIGINAL PROMPT!
Make sure to strictly follow the prompt below, MAKE SURE TO CORRECTLY REFLECT THE COLORS OF ALL OF THE ITEMS, ESPECIALLY WHEN THEY ARE GIVEN IN PANTONE CODING.
Stick to the Pantone color references supplied below.
Also make sure to correctly reflect all the items mentioned in the prompt (especially bed skirt,fitted sheet, flat sheet, coverlet and number of pillowcases).
THE IMAGE MUST BE A FRONT-FACING IMAGE OF THE BED WITH BEDDING ITEMS AND THE WALL BEHIND:\n
"""
        + full_prompt.get("prompt")
        + f"""\nMake sure the image contains the following items: {ITEMS}, and that their respective color is as follows: {ITEMS_STR}
DISREGARD ALL PANTONE MENTIONS and use just Pantone numbers for color references. DO NOT DRAW MORE THAN TWO PILLOWS. DO NOT PUT ANY LOGOS OR TEXT ON THE IMAGE.
DO NOT RENDER ANY PANTONE swatches, icons or references.
"""
    )

    #     pre_prompt = f"""
    # My prompt has full detail so no need to add more. PLEASE DO NOT REWRITE OR MODIFY THE ORIGINAL PROMPT.
    # Make sure to strictly follow the prompt below, MAKE SURE TO CORRECTLY REFLECT THE COLORS AND QUANTITIES OF ALL OF THE ITEMS.
    # Stick to the Pantone color codes in the prompt, unless you are only supplied with a color name.
    # Also make sure to correctly reflect all the items mentioned in the prompt (especially bed skirt,fitted sheet, flat sheet, coverlet and number of pillowcases).
    # DO NOT DRAW MORE THAN TWO PILLOWS.
    # DO NOT REFERENCE OR REFLECT Pantone icons, color swatches etc. on the image!
    # DISREGARD ALL PANTONE MENTIONS and use just Pantone numbers for color references.
    # DO NOT PUT ANY LOGOS OR TEXT ON THE IMAGE.
    # Do not alter the viewing angle, keep it as a side view all the time:\n"""
    #     add_prompt = f"""
    # A photorealistic image of a stack of bedding consisting of the following bedding items - {ITEMS} on a white background.
    # The items are of the following colors: {ITEMS_STR}. The items are laying on top of each other forming a neat stack. The number of items must be strictly observed!
    # """
    #     prompt = pre_prompt + add_prompt
    client = OpenAI(api_key=API_KEY)

    response = client.images.generate(
        model="dall-e-3", prompt=prompt, size=IMG_SIZE, quality="hd", style=STYLE, n=1
    )

    image_url = response.data[0].url
    full_prompt["url"] = image_url
    st.session_state.IMAGES["full"].append(full_prompt)
    return None


#############PAGE LAYOUT##########################################
st.title("Design your bedroom like a pro")
st.subheader("Upload a photo of your bedroom and we'll suggest a few options :smile:")
selector_area = st.empty()
input_area = st.empty()
mode = selector_area.radio(
    "Select editing mode",
    ["Full revision", "Image edit"],
    horizontal=True,
    index=1,
    captions=["Suggest total changes", "Apply changes to your exact image"],
)
input_col, img_col0 = input_area.columns([2, 1])
st.session_state.image_input = input_col.file_uploader(
    "Upload your bedroom photo. Make sure to provide enough light and color details on your image.",
    accept_multiple_files=False,
)
image_area = st.empty()
img_col1, img_col2, img_col3, img_col4, img_col5 = image_area.columns([1, 1, 1, 1, 1])
if st.session_state.image_input:
    resized_image = resize_image(st.session_state.image_input)
    byte_image = convert_image_to_bytes(resized_image)
    st.session_state.encoded_image = encode_image(byte_image)
    img_col0.image(resized_image)
    img_col0.write("Original bedroom")
    if img_col0.button("Reset"):
        st.session_state.IMAGES = {"full": [], "edit": []}

if "encoded_image" in st.session_state:
    with st.spinner("Please wait, working on designs (will take 20-40 seconds)"):
        if st.button("Gimme options!"):
            st.session_state.result = describe_image(st.session_state.encoded_image)
            st.session_state.DONE = True

            if "result" in st.session_state and st.session_state.DONE == True:
                if "error" in st.session_state.result:
                    st.warning(f"Error: {st.session_state.result.get('error')}")
                    st.stop()
                try:
                    IMG_OPTIONS = st.session_state.result.keys()
                    IMG_PROMPTS = [st.session_state.result[x] for x in IMG_OPTIONS]
                    threads = []
                    progress_start = 0
                    my_bar = st.progress(
                        progress_start, "One last step, rendering suggestions"
                    )
                    for prompt in IMG_PROMPTS:
                        if mode == "Full revision":
                            threads.append(
                                threading.Thread(target=generate_image, args=(prompt,))
                            )
                        else:
                            threads.append(
                                threading.Thread(
                                    target=sd_edit, args=(byte_image, prompt)
                                )
                            )

                    for thread in threads:
                        scriptrunner.add_script_run_ctx(thread)
                        thread.start()

                    for thread in threads:
                        thread.join()
                        progress_start += 1 / len(IMG_PROMPTS)
                        my_bar.progress(progress_start)

                    while all(
                        [
                            len(values) < len(IMG_PROMPTS)
                            for values in st.session_state.IMAGES.values()
                        ]
                    ):
                        time.sleep(1)

                except Exception as e:
                    st.error(e)
st.session_state.img_versions = (
    st.session_state.IMAGES["full"]
    if mode == "Full revision"
    else st.session_state.IMAGES["edit"]
)
if "img_versions" in st.session_state and len(st.session_state.img_versions) > 0:
    st.session_state.render_images = list(
        zip(
            [img_col1, img_col2, img_col3, img_col4, img_col5],
            st.session_state.img_versions,
        )
    )
    for col in st.session_state.render_images:
        img = col[1].get("url")
        col[0].image(img)
        col[0].write(
            f"Pillowcases: [{col[1].get('pillowcase')}](https://www.amazon.com/dp/{match_color('pillowcases',col[1].get('pillowcase'), st.session_state.stock)})"
        )
        col[0].write(
            f"Flat sheet: [{col[1].get('flat sheet')}](https://www.amazon.com/dp/{match_color('flat sheet',col[1].get('flat sheet'), st.session_state.stock)})"
        )
        col[0].write(
            f"Fitted sheet: [{col[1].get('fitted sheet')}](https://www.amazon.com/dp/{match_color('fitted sheet',col[1].get('fitted sheet'), st.session_state.stock)})"
        )
        col[0].write(
            f"Bed skirt: [{col[1].get('bed skirt')}](https://www.amazon.com/dp/{match_color('bed skirt',col[1].get('bed skirt','No color'), st.session_state.stock)})"
        )
        col[0].write(
            f"Coverlet: [{col[1].get('coverlet')}](https://www.amazon.com/dp/{match_color('coverlet',col[1].get('coverlet'), st.session_state.stock)})"
        )
        # col[0].write(col[1].get('bed'))
        # col[0].write(col[1].get('prompt'))
    st.write(
        f"Total tokens used: {input_tokens + output_tokens}. Estimated cost: ${(input_tokens * 10 / 1000000) + (output_tokens * 30 / 1000000):.3f}"
    )
