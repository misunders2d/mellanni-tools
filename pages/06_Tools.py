import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO
from modules import formatting as ff
from modules import gcloud_modules as gc
from openai import OpenAI
import time
import pyotp

key = st.secrets["OPENAI_SUMMARIZER_KEY"]
# openai.api_key = key
GPT_MODEL = ["gpt-4", "gpb-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-3.5-turbo-0125"]
model = GPT_MODEL[2]
MAX_TOKENS = 500


st.set_page_config(
    page_title="Mellanni Tools",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)
name_area = st.empty()
col1, col2 = st.columns([10, 3])

from login import require_login

require_login()

user_email = st.user.email
st.write(user_email)

with col2:

    @st.cache_data(show_spinner=False, ttl=3600)
    def pull_dictionary():
        client = gc.gcloud_connect()
        sql = """SELECT * FROM `auxillary_development.dictionary`"""
        query_job = client.query(sql)  # Make an API request.
        dictionary = query_job.result().to_dataframe()
        client.close()
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            dictionary.to_excel(writer, sheet_name="Dictionary", index=False)
            ff.format_header(dictionary, writer, "Dictionary")
        return output.getvalue()

    if col2.checkbox("Dictionary"):
        dictionary = pull_dictionary()
        st.download_button(
            "Download dictionary", dictionary, file_name="Dictionary.xlsx"
        )

with col1:
    with st.expander("OTP codes", icon=":material/qr_code_2:"):
        keys = json.loads(st.secrets["otps"]["users"])

        def otp(text: str):
            global result
            totp = pyotp.TOTP(text.replace(" ", ""))
            result = totp.now()
            return result

        try:
            all_keys = (x for x in keys if user_email in x["emails"])
            sorted_keys = dict()
            for key in keys:
                if user_email in key["emails"]:
                    for data, value in key["data"].items():
                        sorted_keys[data] = value
            sorted_keys = dict(sorted(sorted_keys.items()))
            if sorted_keys:
                otps = {key: otp(item) for key, item in sorted_keys.items()}
                output = "\n".join(
                    f"{k}: ".ljust(50 - len(v)) + v for k, v in sorted(otps.items())
                )
                st.text_area(
                    label="OTPs", value=output, height=200, key=str(time.time())
                )
                if st.button("Refresh", key="OTP refresh"):
                    st.rerun()
        except:
            pass

    with st.expander("Link generator for Seller Central", icon=":material/link:"):
        sc_markets = st.radio(
            "Select marketplace", ["US", "CA"], horizontal=True, key="SC_RADIO"
        )
        domain = "com" if sc_markets == "US" else "ca"
        links_result = []

        def review_links():
            for a in asin_list:
                link = (
                    f"https://www.amazon.{domain}/product-reviews/"
                    + a
                    + "/ref=cm_cr_arp_d_viewopt_fmt?sortBy=recent&pageNumber=1&formatType=current_format"
                )
                links_result.append(link)
            return links_result

        def sc_links():
            for a in asin_list:
                link = f"https://sellercentral.amazon.{domain}/myinventory/inventory?fulfilledBy=all&page=1&pageSize=25&searchField=all&searchTerm={a}&sort=available_desc&status=all&ref_=xx_invmgr_favb_xx"
                # link = f'https://sellercentral.amazon.{domain}/inventory/ref=xx_invmgr_dnav_xx?tbla_myitable=sort:%7B%22sortOrder%22%3A%22ASCENDING%22%2C%22sortedColumnId%22%3A%22skucondition%22%7D;search:'+a+';pagination:1;'
                links_result.append(link)
            return links_result

        def pdp_links():
            for a in asin_list:
                link = f"https://www.amazon.{domain}/dp/" + a
                links_result.append(link)
            return links_result

        def check_prices():
            client = gc.gcloud_connect()
            sql = """SELECT asin, item_name, price FROM `auxillary_development.inventory_report`"""
            query_job = client.query(sql)  # Make an API request.
            inventory = query_job.result().to_dataframe()
            client.close()
            inventory_asin = inventory[inventory["asin"].isin(asin_list)]
            inventory_asin[inventory_asin.columns] = inventory_asin[
                inventory_asin.columns
            ].astype("str")
            # result = (inventory_asin['asin']+' - '+ inventory_asin['price'] + ' - ' + inventory_asin['item_name']).tolist()
            return inventory_asin

        def edit_links():
            client = gc.gcloud_connect()
            sql = """SELECT ASIN,SKU FROM `auxillary_development.dictionary`"""
            query_job = client.query(sql)  # Make an API request.
            dictionary = query_job.result().to_dataframe()
            client.close()
            for a in asin_list:
                dict_asin = dictionary[dictionary["ASIN"] == a]
                sku = dict_asin["SKU"].tolist()  # [0]
                for s in sku:
                    link = f"https://sellercentral.amazon.{domain}/abis/listing/edit?marketplaceID=ATVPDKIKX0DER&ref=xx_myiedit_cont_myifba&sku={s}&asin={a}&productType=HOME_BED_AND_BATH#product_details"
                    links_result.append(link)
            return links_result

        def fix_stranded_inventory():
            for a in asin_list:
                # dict_asin = dictionary[dictionary['ASIN'] == a]
                link = (
                    f"https://sellercentral.amazon.{domain}/inventory?viewId=STRANDED&ref_=myi_ol_vl_fba&tbla_myitable=sort:%7B%22sortOrder%22%3A%22DESCENDING%22%2C%22sortedColumnId%22%3A%22date%22%7D;search:"
                    + a
                    + ";pagination:1;"
                )
                links_result.append(link)
            return links_result

        def order_links():
            for a in asin_list:
                link = (
                    f"https://sellercentral.amazon.{domain}/orders-v3/search?page=1&q="
                    + a
                    + "&qt=asin"
                )
                links_result.append(link)
            return links_result

        functions = {
            "1 - review links": review_links,
            "2 - Seller Central links": sc_links,
            "3 - Product Detail Page links": pdp_links,
            "4 - Check prices in Inventory file": check_prices,
            "5 - Seller Central Edit links": edit_links,
            "6 - Fix Stranded Inventory links": fix_stranded_inventory,
            "7 - Order links": order_links,
        }

        asins = re.split(r"\n|,| ", st.text_area("Input ASINs"))
        options = [x for x in functions.keys()]
        option = st.selectbox("Select an option", options)
        if st.button("Run"):
            asin_list = [x for x in asins if x != ""]
            func = functions[option]
            result = func()
            if isinstance(result, pd.DataFrame):
                result = result.reset_index().drop("index", axis=1)
            st.data_editor(result)

    with st.expander("Process LD results", icon=":material/electric_bolt:"):
        st.markdown(
            "**Note:** This tool has been replaced with a [Chrome Extension](https://chromewebstore.google.com/detail/amazon-ld-manager/lknmibmhladlajjjiccipambbikcchnf?pli=1)"
        )

    with st.expander("Business report link generator", icon=":material/monitoring:"):
        business_markets = st.radio("Select marketplace", ["US", "CA"], horizontal=True)
        domain = "com" if business_markets == "US" else "ca"
        from datetime import datetime, timedelta

        e_date = datetime.now().date() - timedelta(days=2)
        s_date = e_date - timedelta(days=10)
        start = st.date_input("Starting date", value=s_date)
        end = st.date_input("End date", value=e_date)
        numdays = (end - start).days + 1
        date_range = [end - timedelta(days=x) for x in range(numdays)]
        link_list = []
        full_list = []
        for d in date_range:
            link = f"https://sellercentral.amazon.{domain}/business-reports/ref=xx_sitemetric_dnav_xx#/report?id=102%3ADetailSalesTrafficBySKU&chartCols=&columns=0%2F1%2F2%2F3%2F4%2F5%2F6%2F7%2F8%2F9%2F10%2F11%2F12%2F13%2F14%2F15%2F16%2F17%2F18%2F19%2F20%2F21%2F22%2F23%2F24%2F25%2F26%2F27%2F28%2F29%2F30%2F31%2F32%2F33%2F34%2F35%2F36%2F37&fromDate={d.strftime('%Y-%m-%d')}&toDate={d.strftime('%Y-%m-%d')}"
            link_list.append(link)
            full_list = "  \n  \n".join(link_list)
        if st.button("Generate") and full_list:
            st.text_area("Generated links", full_list)

    with st.expander("Pricelist checker"):
        import pandas as pd
        import numpy as np

        def linspace(df, steps):
            result = np.linspace(df["Standard Price"], df["MSRP"], steps)
            return result

        def add_steps(file_path, steps):
            file = pd.read_excel(
                file_path,
                usecols=[
                    "Collection",
                    "SKU",
                    "ASIN",
                    "Size",
                    "Color",
                    "Standard Price",
                    "MSRP",
                ],
            )
            file["steps"] = file.apply(linspace, steps=steps + 1, axis=1)

            for i in range(0, steps + 1):
                file[f"step {i}"] = file["steps"].apply(lambda x: round(x[i], 2))
            for i in range(0, steps):
                file[f"% {i+1}"] = file[f"step {i+1}"] / file[f"step {i}"] - 1
            del file["steps"]
            del file["step 0"]
            return file

    with st.expander("Backend checker", icon=":material/code:"):

        def process_backend(files):
            to_df = []
            for file in files:
                file = file.getvalue()
                result = json.loads(file.decode("utf-8"))

                kw_fields = [
                    x
                    for x in result["detailPageListingResponse"].keys()
                    if "keyword" in x.lower()
                ]
                if not kw_fields:
                    break
                asin = result["detailPageListingResponse"]["asin"]["value"]
                try:
                    brand = result["detailPageListingResponse"]["brand#1.value"][
                        "value"
                    ]
                except:
                    try:
                        brand = result["detailPageListingResponse"]["brand"]["value"]
                    except:
                        brand = "Unknown"
                platinum = [
                    x
                    for x in result["detailPageListingResponse"].keys()
                    if "platinum" in x.lower()
                ]
                pkw = []
                for p in platinum:
                    pkw.append(result["detailPageListingResponse"][p]["value"])
                pkw = " ".join(pkw)
                try:
                    size = result["detailPageListingResponse"]["size#1.value"]["value"]
                except:
                    size = result["detailPageListingResponse"]["size_name"]["value"]
                try:
                    color = result["detailPageListingResponse"]["color#1.value"][
                        "value"
                    ]
                except:
                    color = result["detailPageListingResponse"]["color_name"]["value"]
                try:
                    kws = result["detailPageListingResponse"][
                        "generic_keyword#1.value"
                    ][
                        "value"
                    ]  # .split(' ')
                except:
                    kws = result["detailPageListingResponse"]["generic_keywords"][
                        "value"
                    ]  # .split(' ')
                try:
                    title = result["detailPageListingResponse"]["item_name#1.value"][
                        "value"
                    ]
                except:
                    title = result["detailPageListingResponse"]["item_name"]["value"]
                to_df.append([asin, brand, size, color, kws, pkw, title])
            df = pd.DataFrame(
                to_df,
                columns=[
                    "asin",
                    "brand",
                    "size",
                    "color",
                    "kws",
                    "platinum kws",
                    "title",
                ],
            )
            return df

        markets = ["USA", "CA", "UK", "DE", "FR", "IT", "SP"]
        market = st.radio("Select marketplace", markets, horizontal=True)
        extensions = ["com", "ca", "co.uk", "de", "fr", "it", "sp"]
        choice = dict(zip(markets, extensions))
        data_area = st.empty()
        asin_col, links_col = data_area.columns([1, 3])
        button_area = st.empty()
        but1, but2, but3 = button_area.columns([1, 1, 1])
        link = f"https://sellercentral.amazon.{choice[market]}/abis/ajax/reconciledDetailsV2?asin="
        asins = asin_col.text_area("Input ASINs to parse").split("\n")
        if but1.button("Get links"):
            st.session_state["asins"] = True
            links_col.text_area("Links:", "\n".join(link + asin for asin in asins))
        if "asins" in st.session_state:
            files = st.file_uploader(
                "Upload files", type=".json", accept_multiple_files=True
            )
            if files:
                final = process_backend(files)
                st.write(final)
                output = BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    final.to_excel(writer, sheet_name="KW", index=False)
                    ff.format_header(final, writer, "KW")
                st.download_button(
                    "Download results", output.getvalue(), file_name="backend.xlsx"
                )
        if but3.button("Reset") and "asins" in st.session_state:
            del st.session_state["asins"]

    with st.expander(
        "Convert GDrive links to direct links", icon=":material/add_to_drive:"
    ):
        import re

        links_area = st.empty()

        def clean_links(links):
            clean = []
            for i in links:
                c = i.replace("https://drive.google.com/file/d/", "").replace(
                    "/view?usp=sharing", ""
                )
                c = c.replace("https://drive.google.com/open?id=", "").split(
                    "&authuser="
                )[0]
                c = "https://drive.google.com/uc?export=view&id=" + c
                clean.append(c)
            return clean

        links = re.split(",|\n", links_area.text_area("Input links to convert"))
        links = [x for x in links if x != ""]
        if st.button("Convert"):
            new_links = clean_links(links)
            links_area.text_area("Clean links", "\n\n".join(new_links))
    with st.expander(
        "Upload images to web and get direct links",
        expanded=False,
        icon=":material/imagesmode:",
    ):
        st.warning(
            body="This tool has moved to [a separate page](https://mellanni-tools.streamlit.app/Images)",
            icon=":material/moved_location:",
        )

    with st.expander("Meeting summarizer", expanded=False, icon=":material/summarize:"):
        st.warning(
            "Deprecated, use Gemini or any other available chatbot instead",
            icon=":material/adb:",
        )
