import sys
import types

fake_streamlit = types.SimpleNamespace(
    secrets={
        "AMZ_REFRESH_TOKEN_US": "test",
        "AMZ_SELLER_ID": "test",
        "AMZ_CLIENT_ID": "test",
        "AMZ_CLIENT_SECRET": "test",
        "gcp_service_account": {},
    }
)
sys.modules["streamlit"] = fake_streamlit

import google.oauth2.service_account as service_account  # noqa: E402

service_account.Credentials = types.SimpleNamespace(
    from_service_account_info=lambda _info: object()
)

from modules import sc_modules as sc  # noqa: E402


class FakeListing:
    def __init__(self, attributes):
        self.payload = {"attributes": attributes, "summaries": [{"productType": "BED_LINEN_SET"}]}


def _offer(audience, price, marketplace_id="ATVPDKIKX0DER", currency="USD"):
    return {
        "marketplace_id": marketplace_id,
        "currency": currency,
        "audience": audience,
        "our_price": [{"schedule": [{"value_with_tax": price}]}],
    }


def test_extract_prices_prefers_all_offer_over_b2b():
    listing = FakeListing(
        {
            "purchasable_offer": [
                _offer("B2B", 35.61),
                _offer("ALL", 37.97),
            ],
            "list_price": [
                {"marketplace_id": "ATVPDKIKX0DER", "currency": "USD", "value": "50.97"}
            ],
        }
    )

    prices = sc.extract_prices_from_listing(listing)

    assert prices["our_price"] == 37.97
    assert prices["list_price"] == "50.97"
    assert prices["currency"] == "USD"


def test_extract_prices_skips_b2b_only_offer():
    listing = FakeListing({"purchasable_offer": [_offer("B2B", 35.61)]})

    prices = sc.extract_prices_from_listing(listing)

    assert prices["our_price"] is None


def test_extract_prices_uses_unknown_audience_fallback_but_not_b2b():
    listing = FakeListing(
        {
            "purchasable_offer": [
                _offer("B2B", 35.61),
                _offer(None, 37.97),
            ]
        }
    )

    prices = sc.extract_prices_from_listing(listing)

    assert prices["our_price"] == 37.97


def test_extract_prices_prefers_requested_marketplace_all_offer():
    listing = FakeListing(
        {
            "purchasable_offer": [
                _offer("ALL", 29.99, marketplace_id="WRONG"),
                _offer("ALL", 37.97, marketplace_id="ATVPDKIKX0DER"),
            ]
        }
    )

    prices = sc.extract_prices_from_listing(listing)

    assert prices["our_price"] == 37.97
