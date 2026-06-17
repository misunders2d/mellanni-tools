import os
import time
from typing import List, Literal, TypedDict

import requests
import streamlit as st
from dotenv import load_dotenv
from google.oauth2 import service_account
from sp_api.api import ListingsItems

load_dotenv()

REFRESH_TOKEN_US = os.environ.get(
    "AMZ_REFRESH_TOKEN_US", st.secrets["AMZ_REFRESH_TOKEN_US"]
)
SELLER_ID = os.environ.get("AMZ_SELLER_ID", st.secrets["AMZ_SELLER_ID"])
MARKETPLACE_IDS = MARKETPLACE_IDS = ["ATVPDKIKX0DER"]

positions_mapping = {
    "main_image": "main_product_image_locator",
    "other_image_1": "other_product_image_locator_1",
    "other_image_2": "other_product_image_locator_2",
    "other_image_3": "other_product_image_locator_3",
    "other_image_4": "other_product_image_locator_4",
    "other_image_5": "other_product_image_locator_5",
    "other_image_6": "other_product_image_locator_6",
    "other_image_7": "other_product_image_locator_7",
    "other_image_8": "other_product_image_locator_8",
    "swatch_image": "swatch_product_image_locator",
}

GC_CREDENTIALS = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)


def get_amazon_credentials():
    credentials = dict(
        refresh_token=REFRESH_TOKEN_US,
        lwa_app_id=os.environ.get("AMZ_CLIENT_ID", st.secrets["AMZ_CLIENT_ID"]),
        lwa_client_secret=os.environ.get(
            "AMZ_CLIENT_SECRET", st.secrets["AMZ_CLIENT_SECRET"]
        ),
    )
    return credentials


def get_access_token():
    LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
    credentials = get_amazon_credentials()

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": credentials["refresh_token"],
        "client_id": credentials["lwa_app_id"],
        "client_secret": credentials["lwa_client_secret"],
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}

    try:
        lwa_response = requests.post(LWA_TOKEN_URL, data=payload, headers=headers)
        lwa_response.raise_for_status()  # Raise an exception for HTTP errors

        lwa_data = lwa_response.json()
        access_token = lwa_data.get("access_token")
        expires_in = lwa_data.get("expires_in")  # Typically 3600 seconds (1 hour)

        if access_token:
            print(
                f"Successfully obtained LWA Access Token. Expires in {expires_in} seconds."
            )
            return access_token
        else:
            print("Failed to get LWA Access Token from response.")

    except requests.exceptions.RequestException as e:
        print(f"Error exchanging refresh token for LWA Access Token: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"LWA Response error: {e.response.text}")


def extract_sku_images(listing_details):
    images = listing_details.payload["attributes"]
    image_lists = [x for x in images if "product_image_locator" in x]
    image_links = {x: images[x][0]["media_location"] for x in image_lists}
    reverse_mapping = {v: k for k, v in positions_mapping.items()}
    image_links = {reverse_mapping.get(k, k): v for k, v in image_links.items()}

    return image_links


def get_listing_details(
    sku: str,
    include: List[
        Literal[
            "summaries",
            "attributes",
            "issues",
            "offers",
            "fulfillmentAvailability",
            "procurement",
            "relationships",
            "productTypes",
        ]
    ],
):
    listings_client = ListingsItems(credentials=get_amazon_credentials())
    try:
        response = listings_client.get_listings_item(
            sellerId=SELLER_ID, sku=sku, includedData=include
        )
    except Exception:
        return
    return response


class ImageAttributes(TypedDict, total=False):
    main_product_image_locator: str
    other_product_image_locator_1: str
    other_product_image_locator_2: str
    other_product_image_locator_3: str
    other_product_image_locator_4: str
    other_product_image_locator_5: str
    other_product_image_locator_6: str
    other_product_image_locator_7: str
    other_product_image_locator_8: str
    swatch_product_image_locator: str


def update_sc_image(
    sku: str,
    product_type: str,
    op: Literal["replace", "delete"] = "replace",
    images: ImageAttributes = {},
) -> str:
    time.sleep(0.2)  # To avoid hitting API rate limits
    listings_client = ListingsItems(credentials=get_amazon_credentials())
    patch_body = {
        "productType": product_type,
        "patches": [
            {
                "op": op,
                "path": f"/attributes/{position}",
                "value": [{"media_location": link}],
            }
            for position, link in images.items()
        ],
    }

    try:
        response = listings_client.patch_listings_item(
            sellerId=SELLER_ID, sku=sku, marketplaceIds=MARKETPLACE_IDS, body=patch_body
        )
        image_names = "\n".join(images)
        return f"{op.upper()} SUCCESS for {sku} with status {response.payload['status']}:\n {image_names}\n\n"
    except Exception as e:
        return f"ERROR: failed to {op} image for {sku}:\n{e}"


def push_images_to_amazon(
    skus: list, images_to_push: dict, action: Literal["replace", "delete"] = "replace"
) -> list[str]:

    image_paths = {
        positions_mapping[position]: link
        for position, link in images_to_push.items()
        if position in positions_mapping
    }
    new_links = ImageAttributes(**image_paths)
    response = get_listing_details(skus[0], include=["summaries"])
    if response and response.payload["summaries"]:
        product_type = response.payload["summaries"][0]["productType"]
    elif response and not response.payload["summaries"]:
        product_type = "BED_LINEN_SET"
    else:
        return [f"ERROR: Could not retrieve product type for SKU {skus[0]}"]
    results = []
    for sku in skus:
        results.append(
            update_sc_image(
                sku=sku, product_type=product_type, op=action, images=new_links
            )
        )
    return results


def extract_prices_from_listing(
    listing_details, marketplace_id: str = "ATVPDKIKX0DER"
) -> dict:
    if not listing_details or not getattr(listing_details, "payload", None):
        return {
            "our_price": None,
            "list_price": None,
            "currency": None,
            "product_type": None,
        }

    payload = listing_details.payload
    attrs = payload.get("attributes", {}) or {}

    our_price = None
    currency = None
    marketplace_offers = [
        offer
        for offer in attrs.get("purchasable_offer", []) or []
        if not offer.get("marketplace_id") or offer["marketplace_id"] == marketplace_id
    ]
    preferred_offers = [
        offer
        for offer in marketplace_offers
        if str(offer.get("audience") or "").upper() in {"ALL", "B2C"}
    ]
    fallback_offers = [
        offer
        for offer in marketplace_offers
        if str(offer.get("audience") or "").upper() not in {"ALL", "B2C", "B2B"}
    ]

    # Listings can contain separate B2B and consumer offers. The pricing UI shows
    # Seller Central's consumer price, so prefer ALL/B2C and never use B2B.
    for offer in preferred_offers + fallback_offers:
        schedule = (offer.get("our_price") or [{}])[0].get("schedule") or []
        if schedule:
            our_price = schedule[0].get("value_with_tax")
        if our_price is not None:
            currency = offer.get("currency") or currency
            break

    list_price = None
    for lp in attrs.get("list_price", []) or []:
        if lp.get("marketplace_id") and lp["marketplace_id"] != marketplace_id:
            continue
        list_price = lp.get("value", lp.get("value_with_tax"))
        if not currency:
            currency = lp.get("currency")
        if list_price is not None:
            break

    summaries = payload.get("summaries", []) or []
    product_type = summaries[0].get("productType") if summaries else None

    return {
        "our_price": our_price,
        "list_price": list_price,
        "currency": currency or "USD",
        "product_type": product_type,
    }


def get_sku_prices(sku: str) -> dict:
    response = get_listing_details(sku, include=["attributes", "summaries"])
    prices = extract_prices_from_listing(response)
    prices["sku"] = sku
    prices["found"] = response is not None
    return prices


def update_listing_prices(
    sku: str,
    product_type: str,
    our_price=None,
    list_price=None,
    currency: str = "USD",
    marketplace_id: str = "ATVPDKIKX0DER",
) -> str:
    time.sleep(0.2)
    patches = []
    applied = []

    if our_price is not None:
        patches.append(
            {
                "op": "replace",
                "path": "/attributes/purchasable_offer",
                "value": [
                    {
                        "marketplace_id": marketplace_id,
                        "currency": currency,
                        "our_price": [
                            {"schedule": [{"value_with_tax": float(our_price)}]}
                        ],
                    }
                ],
            }
        )
        applied.append(f"our_price={float(our_price):.2f}")

    if list_price is not None:
        patches.append(
            {
                "op": "replace",
                "path": "/attributes/list_price",
                "value": [
                    {
                        "marketplace_id": marketplace_id,
                        "currency": currency,
                        "value": float(list_price),
                    }
                ],
            }
        )
        applied.append(f"list_price={float(list_price):.2f}")

    if not patches:
        return f"SKIP: no prices provided for {sku}"

    listings_client = ListingsItems(credentials=get_amazon_credentials())
    body = {"productType": product_type, "patches": patches}

    try:
        response = listings_client.patch_listings_item(
            sellerId=SELLER_ID, sku=sku, marketplaceIds=MARKETPLACE_IDS, body=body
        )
        return (
            f"SUCCESS: {sku} status={response.payload['status']} "
            f"({', '.join(applied)})"
        )
    except Exception as e:
        return f"ERROR: failed to update prices for {sku}: {e}"
