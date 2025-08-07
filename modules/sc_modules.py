import os, requests
from sp_api.api import ListingsItems
from typing import List, Literal
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

REFRESH_TOKEN_US=os.environ.get('AMZ_REFRESH_TOKEN_US', st.secrets['AMZ_REFRESH_TOKEN_US'])
SELLER_ID = os.environ.get('AMZ_SELLER_ID', st.secrets['AMZ_SELLER_ID'])
MARKETPLACE_IDS = MARKETPLACE_IDS=["ATVPDKIKX0DER"]

SKU = 'M-TH-BLANKET-CASHM-QUEEN-HBONE-YELLOW'

def get_amazon_credentials():
    credentials = dict(
        refresh_token=REFRESH_TOKEN_US,
        lwa_app_id=os.environ.get('AMZ_CLIENT_ID', st.secrets['AMZ_CLIENT_ID']),
        lwa_client_secret=os.environ.get('AMZ_CLIENT_SECRET', st.secrets['AMZ_CLIENT_SECRET'])
    )
    return credentials


def get_access_token():
    LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
    credentials = get_amazon_credentials()

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": credentials["refresh_token"],
        "client_id": credentials["lwa_app_id"],
        "client_secret": credentials["lwa_client_secret"]
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
    }

    try:
        lwa_response = requests.post(LWA_TOKEN_URL, data=payload, headers=headers)
        lwa_response.raise_for_status() # Raise an exception for HTTP errors

        lwa_data = lwa_response.json()
        access_token = lwa_data.get("access_token")
        expires_in = lwa_data.get("expires_in") # Typically 3600 seconds (1 hour)

        if access_token:
            print(f"Successfully obtained LWA Access Token. Expires in {expires_in} seconds.")
            return access_token
        else:
            print("Failed to get LWA Access Token from response.")

    except requests.exceptions.RequestException as e:
        print(f"Error exchanging refresh token for LWA Access Token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"LWA Response error: {e.response.text}")
            

def get_listing_details(
    sku: str,
    include: List[Literal[
        'summaries', 'attributes', 'issues', 'offers', 'fulfillmentAvailability', 'procurement', 'relationships', 'productTypes']
        ]
    ):
    
    listings_client = ListingsItems(credentials=get_amazon_credentials())
    response = listings_client.get_listings_item(
        sellerId=SELLER_ID,
        sku=sku,
        includedData=include
    )
    return response


def update_image(
        sku,
        product_type,
        image_path,
        op: Literal['replace','delete']='replace',
        attribute_paths: List[Literal[
            'main_product_image_locator','other_product_image_locator_1',
            'other_product_image_locator_2','other_product_image_locator_3',
            'other_product_image_locator_4','other_product_image_locator_5',
            'other_product_image_locator_6','other_product_image_locator_7',
            'other_product_image_locator_8','swatch_product_image_locator',
            ]]=[]
        ):

    listings_client = ListingsItems(credentials=get_amazon_credentials())
    patch_body = {
        "productType": product_type,
        "patches": [
            {
                "op": op,
                "path": f"/attributes/{attribute_path}",
                "value": [
                    {
                        "media_location": image_path
                    }
                ]
            }
            for attribute_path in attribute_paths
        ]
    }
    
    
    try:
        response = listings_client.patch_listings_item(
            sellerId=SELLER_ID,
            sku=sku,
            marketplaceIds=MARKETPLACE_IDS,
            body=patch_body
        )
        print(f"Image updated for {sku} with status {response.payload['status']}\nImage: {image_path}\n\n")
    except Exception as e:
        print(f"FAILED to update image for {sku}:\n{e}")
        return e

def push_images_to_amazon(product: str, color: str, size: str, position: str, image_url: str) -> None:
    """
    Placeholder function for pushing images to Amazon seller central.
    This function should be implemented with the actual logic for uploading images to Amazon S3.
    """
    raise NotImplementedError("This function needs to be implemented.")