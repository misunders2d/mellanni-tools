import os
from google.adk.models.lite_llm import LiteLlm
import streamlit as st
from datetime import datetime


OPENAI_API_KEY = os.environ.get("OPENAI_AGENTS_API_KEY")

MODEL = "gemini-2.5-flash"
# MODEL = LiteLlm('openai/gpt-4o-mini', api_key=OPENAI_API_KEY)
SEARCH_AGENT_MODEL = "gemini-2.5-flash-lite"
CREATIVES_AGENT_MODEL = "gemini-2.5-flash"


def get_user_email():
    return st.user.get("email", "Unknown User")


def get_username():
    return st.user.get("name", "Unknown User")


def get_username_str():
    return (
        f"The user's name is {get_username()}."
        if get_username() != "Unknown User"
        else "The user's name is not available."
    )


def get_current_datetime():
    """A helper function used to retrieve current date and time. Use it when you need to be time-aware."""
    return datetime.now()


table_data = {
    "auxillary_development": {
        "dataset_description": "additional dataset for Amazon sales channels",
        "tables": {
            "all_order_report": {"description": "Obsolete table, do not use"},
            "amazon_fulfilled_orders": {"description": "Obsolete table, do not use"},
            "attribution": {"description": "Obsolete table, do not use"},
            "dashboard": {"description": ""},
            "dictionary": {
                "description": "A mapping table (dictionary), containing all the necessary ASIN and SKU mapping data for USA. Be careful when joining this table on ASINs, as they contain multiple duplicate values.",
            },
            "dictionary_ca": {
                "description": "A mapping table (dictionary), containing all the necessary ASIN and SKU mapping data for Canada. Be careful when joining this table on ASINs, as they contain multiple duplicate values.",
            },
            "dictionary_eu": {
                "description": "A mapping table (dictionary), containing all the necessary ASIN and SKU mapping data for Europe. Be careful when joining this table on ASINs, as they contain multiple duplicate values.",
            },
            "dictionary_shp": {
                "description": "A mapping table (dictionary), containing all the necessary SKU mapping data for Shopify",
            },
            "dictionary_uk": {
                "description": "A mapping table (dictionary), containing all the necessary ASIN and SKU mapping data for United Kingdom. Be careful when joining this table on ASINs, as they contain multiple duplicate values.",
            },
            "dictionary_wm": {
                "description": "A mapping table (dictionary), containing all the necessary SKU mapping data for Walmart.",
            },
            "dimensions": {"description": ""},
            "inventory_report": {
                "description": "Old inventory table, do not use",
            },
            "keywords_de": {"description": ""},
            "keywords_fr": {"description": ""},
            "keywords_uk": {"description": ""},
            "keywords_us": {"description": ""},
            "matt": {"description": ""},
            "price_comparison": {"description": ""},
            "promotions": {"description": ""},
            "restock_inventory": {"description": ""},
            "reviews_us": {"description": ""},
            "scp_asin_weekly": {"description": ""},
            "sku_changelog": {
                "description": "A changelog containing all the records for changes that could impact sales performance (per SKU) for USA Amazon",
            },
            "sku_changelog_ca": {
                "description": "A changelog containing all the records for changes that could impact sales performance (per SKU) for Canada Amazon",
            },
            "sku_changelog_de": {"description": ""},
            "sku_changelog_es": {"description": ""},
            "sku_changelog_fr": {"description": ""},
            "sku_changelog_it": {"description": ""},
            "sku_changelog_uk": {"description": ""},
            "sqp_brand_weekly": {"description": ""},
        },
    },
    "clickup": {
        "dataset_description": "Dataset containg different Clickup related tables",
        "tables": {
            "active_projects_tasks": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "active_spaces_tasks": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "clickup_tasks": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "clickup_tasks_hist": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "projects_statuses": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "spaces_statuses": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "tasks_report": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "tasks_report_hist": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
        },
    },
    "daily_reports": {
        "dataset_description": "A buffer dataset containing Amazon related data refreshed daily, do not use",
        "tables": {
            "pricelist": {"description": ""},
            "restock": {"description": ""},
        },
    },
    "ds_for_bi": {
        "dataset_description": "A combined dataset from multiple sources, used primarily as a source for PowerBi reports.",
        "tables": {
            "abc_analysis_dumps": {"description": ""},
            "ad_internal_amz": {"description": ""},
            "ad_internal_amz_api": {"description": ""},
            "amazon_attribution_tags": {"description": ""},
            "amazon_attribution_view": {"description": ""},
            "amazon_creators": {"description": ""},
            "amazon_daily": {"description": ""},
            "amz_sales_deviation_180d": {"description": ""},
            "ana_data": {"description": ""},
            "aspire_manual_samples": {"description": ""},
            "bq_table_meta_data": {"description": ""},
            "check": {"description": ""},
            "classified_reviews": {"description": ""},
            "cogs": {"description": ""},
            "cogs_calculation_gsheet": {"description": ""},
            "cogs_calculations_results": {"description": ""},
            "cogs_calulation_data": {"description": ""},
            "container_processing_collections_pivot": {
                "description": "",
            },
            "container_processing_view": {"description": ""},
            "container_processing_view_old": {"description": ""},
            "creators_connections_rep": {"description": ""},
            "creators_pivot_view": {"description": ""},
            "daily_targets": {"description": ""},
            "daily_targets_high_level": {"description": ""},
            "date_range_all_countries": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "date_range_business_report": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "date_range_depr_view": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "date_range_report_test": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "date_range_summary_v2": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "deals_group": {"description": ""},
            "dictionary": {"description": ""},
            "dictionary_fbm_missed": {"description": ""},
            "dictionary_inv_statuses_hist": {"description": ""},
            "dictionary_items_in_box": {"description": ""},
            "driven_promo_revenue": {"description": ""},
            "driven_promo_view": {"description": ""},
            "dsp_direct_spend": {"description": ""},
            "dsp_total_spend": {"description": ""},
            "events_calendar": {"description": ""},
            "fba_inv_missed_dates": {"description": ""},
            "fba_inventory_partitioned": {"description": ""},
            "fba_storage_fees_calculation_data": {
                "description": "",
            },
            "flags_iso": {"description": ""},
            "giveaway_expenses": {"description": ""},
            "giveaway_revenue": {"description": ""},
            "influencers_expenses": {"description": ""},
            "large_orders": {"description": ""},
            "ld_order_details": {"description": ""},
            "ld_order_details_all_orders": {"description": ""},
            "lightning_deals": {"description": ""},
            "lightning_deals_report": {"description": ""},
            "lightning_deals_view": {"description": ""},
            "lost_prevented_overstock_products": {
                "description": "",
            },
            "lost_sales": {"description": ""},
            "lost_sales_full_data": {"description": ""},
            "lost_sales_hist": {"description": ""},
            "lost_sales_v2": {"description": ""},
            "lost_sales_v3_data": {"description": ""},
            "maverickx_daily": {"description": ""},
            "meta_fb_posts_hist": {"description": ""},
            "meta_fb_posts_hist_2": {"description": ""},
            "meta_instagram_post_hist": {"description": ""},
            "overstock_products": {"description": ""},
            "performance_summary": {"description": ""},
            "pivot_sales_180d_by_ch": {"description": ""},
            "prices_history": {"description": ""},
            "product_cost_hist": {"description": ""},
            "sales_and_returns_allorders_view": {
                "description": "",
            },
            "samples_pivot": {"description": ""},
            "samples_provided_to_influencers": {"description": ""},
            "samples_with_shipping_cost": {"description": ""},
            "scorecard_general_measures": {"description": ""},
            "sellecloud_transit_to_wh": {"description": ""},
            "storage_fees_addition": {"description": ""},
            "storage_fees_amz_estim_and_plan": {"description": ""},
            "storage_fees_fba_inv_planning": {"description": ""},
            "storefront_insights_view": {"description": ""},
            "storefront_pages_mapper": {"description": ""},
            "target_wos_by_sku": {"description": ""},
            "targets": {"description": ""},
            "targets_calc": {"description": ""},
            "targets_calc_all_channels": {"description": ""},
            "tiktok_orders": {"description": ""},
            "update_freq_norms": {"description": ""},
            "walmart_restock": {"description": ""},
            "walmart_restock_2": {"description": ""},
            "zendesk": {"description": ""},
        },
    },
    "ebay": {
        "dataset_description": "Ecom information about company's ebay business",
        "tables": {
            "orders": {"description": ""},
            "payout": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "promoted_listings_general": {"description": ""},
            "promoted_listings_priority": {"description": ""},
            "transactions": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
        },
    },
    "facebook": {
        "dataset_description": "Facebook Ads and posts data",
        "tables": {
            "attribution_facebook": {"description": ""},
            "facebook_posts": {"description": ""},
            "facebook_posts_copy": {"description": ""},
            "insights": {"description": ""},
            "instagram_posts": {"description": ""},
        },
    },
    "google": {
        "dataset_description": "Dataset for data from Google ad campaigns, external marketing data",
        "tables": {
            "ads_report": {"description": ""},
            "conversions_report": {"description": ""},
            "google_vs_pinterest": {"description": ""},
            "google_vs_pinterest_": {"description": ""},
        },
    },
    "hurma": {
        "dataset_description": "HR related dataset.",
        "tables": {
            "candidates": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "careers": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "clickup_candidates": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "clickup_contact_list": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "clickup_job_posting": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "clickup_pto_calendar": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "departments": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "employees": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "employees_archive": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "out_off_office": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "stages": {"description": "", "authorized_users": ["valerii@mellanni.com"]},
            "teams": {"description": "", "authorized_users": ["valerii@mellanni.com"]},
            "temp_workers": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "temp_workers_pb": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "tenure": {"description": "", "authorized_users": ["valerii@mellanni.com"]},
            "vacancies": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
        },
    },
    "klaviyo": {
        "dataset_description": "",
        "tables": {
            "campaign_values": {"description": ""},
            "campaigns_details": {"description": ""},
            "flow_series": {"description": ""},
        },
    },
    "kustomer": {
        "dataset_description": "",
        "tables": {"diff_report": {"description": ""}},
    },
    "levanta": {
        "dataset_description": "",
        "tables": {
            "brands": {"description": ""},
            "brb_reports": {"description": ""},
            "click_reports": {"description": ""},
            "creators": {"description": ""},
            "products": {"description": ""},
            "summary_performance": {"description": ""},
            "test_groups": {"description": ""},
        },
    },
    "lookerstudio_ds": {
        "dataset_description": "",
        "tables": {
            "ana_meta_tracker": {"description": ""},
            "meta_marketing_insights": {"description": ""},
        },
    },
    "pinterest": {
        "dataset_description": "",
        "tables": {"ads_analytics": {"description": ""}},
    },
    "reports": {
        "dataset_description": "The main dataset for the company's Amazon business data. Includes data from multiple Amazon channels (amazon.com, amazon.ca etc.), including sales data which came from outside of Amazon, but was fulfilled by Amazon.",
        "tables": {
            "AdvertisedProduct": {"description": ""},
            "PurchasedProduct": {"description": ""},
            "SponsoredBrandsPlacement": {"description": ""},
            "SponsoredDisplay": {"description": ""},
            "SponsoredProductsPlacement": {"description": ""},
            "active_listing_report": {"description": ""},
            "aged_inventory_surcharge": {"description": ""},
            "all_listing_report": {"description": ""},
            "all_orders": {
                "description": "A table with all orders information for Amazon, including off-amazon sales which were fulfilled by Amazon",
            },
            "all_orders_usd": {"description": ""},
            "attribution": {"description": ""},
            "awd_inventory": {"description": ""},
            "awd_shipments": {"description": ""},
            "awd_shipments_details": {"description": ""},
            "business_report": {
                "description": "One of the main tables showing sales data including Sessions (organic impressions) on an SKU level. Do not use for conversion calculations.",
            },
            "business_report_asin": {
                "description": "One of the main tables showing sales data including Sessions (organic impressions) on an ASIN level. Use for conversion calculations.",
            },
            "date_range_report": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "dictionary": {"description": ""},
            "dsp_report": {"description": ""},
            "exchange_rates": {"description": ""},
            "fba_inventory": {"description": ""},
            "fba_inventory_partitioned": {"description": ""},
            "fba_inventory_planning": {
                "description": "Main table containing all necessary inventory information for multiple Amazon marketplaces",
            },
            "fba_inventory_planning_copy": {"description": ""},
            "fba_returns": {"description": ""},
            "fee_preview": {"description": ""},
            "fee_preview_usd": {"description": ""},
            "fulfilled_inventory": {"description": ""},
            "inventory": {"description": ""},
            "profitability": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "profitability_view": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "promotions": {"description": ""},
            "reserved_inventory": {"description": ""},
            "restock_inventory": {"description": ""},
            "settlement": {
                "description": "",
                "authorized_users": ["sergey@mellanni.com", "valerii@mellanni.com"],
            },
            "settlement_daily": {
                "description": "",
                "authorized_users": ["sergey@mellanni.com", "valerii@mellanni.com"],
            },
            "settlement_daily_usd": {
                "description": "",
                "authorized_users": ["sergey@mellanni.com", "valerii@mellanni.com"],
            },
            "shipments": {
                "description": "Amazon fulfilled orders (excluding FBM shipments), crucial table for building a Promotions report",
            },
            "sponsored_brands_all": {"description": ""},
            "sponsored_brands_video": {"description": ""},
            "sponsored_display": {"description": ""},
            "storage_fee": {"description": ""},
            "storage_fee_usd": {"description": ""},
            "store_insights_asin": {"description": ""},
            "store_insights_date": {"description": ""},
            "store_insights_pages": {"description": ""},
        },
    },
    "sellercloud": {
        "dataset_description": "A company's invnentory dataset, containing tables on the warehouse invnetory, bins, incoming PO's etc, coming from Sellercloud software",
        "tables": {
            "fba_shipments": {"description": ""},
            "fba_shipments_partitioned": {"description": ""},
            "inventory": {"description": ""},
            "inventory_bins": {"description": ""},
            "inventory_bins_partitioned": {"description": ""},
            "inventory_bins_report": {"description": ""},
            "inventory_partitioned": {"description": ""},
            "orders": {"description": ""},
            "purchase_orders": {"description": ""},
            "purchase_orders_saved_and_pending": {
                "description": "",
            },
            "warehouse_bin_movements": {"description": ""},
        },
    },
    "shipstation": {
        "dataset_description": "",
        "tables": {
            "samples_shipments": {"description": ""},
            "samples_shipments_cost": {"description": ""},
            "shipstation_orders": {"description": ""},
            "shipstation_orders_temp": {"description": ""},
            "shipstation_shipments": {"description": ""},
            "shipstation_stores": {"description": ""},
            "shipstation_tags": {"description": ""},
        },
    },
    "shopify": {
        "dataset_description": "Ecom information about company's Shopify business",
        "tables": {
            "abandoned_checkouts": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "customers": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "ebay_vs_shopify": {"description": ""},
            "inventory": {"description": ""},
            "ordered_products": {"description": ""},
            "orders": {"description": ""},
        },
    },
    "skai": {
        "dataset_description": "A PPC related dataset with data points from the Skai software for the company's Amazon advertising",
        "tables": {
            "campaigns_info": {"description": ""},
            "campaigns_performance": {"description": ""},
            "campaigns_performance_v2": {"description": ""},
        },
    },
    "slack": {
        "dataset_description": "List of users of the company's Slack workspace",
        "tables": {
            "users_list": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            }
        },
    },
    "supply_chain": {
        "dataset_description": "",
        "tables": {
            "aged_inventory_surcharge": {"description": ""},
            "awd_inventory": {"description": ""},
            "awd_shipments": {"description": ""},
            "awd_shipments_details": {"description": ""},
            "business_report": {"description": ""},
            "fba_inventory": {"description": ""},
            "manage_fba_Inventory": {"description": ""},
            "monthly_storage_fee": {"description": ""},
            "reserved_inventory": {"description": ""},
            "restock_inventory": {"description": ""},
            "sellercloud_fba_shipments": {"description": ""},
            "sellercloud_fba_shipments_partitioned": {
                "description": "",
            },
            "sellercloud_inventory": {"description": ""},
            "sellercloud_inventory_bins": {"description": ""},
            "sellercloud_inventory_bins_partitioned": {
                "description": "",
            },
            "sellercloud_inventory_partitioned": {
                "description": "",
            },
            "sellercloud_orders": {"description": ""},
            "sellercloud_purchase_orders": {"description": ""},
            "sellercloud_wh_bin_movements": {"description": ""},
        },
    },
    "target": {
        "dataset_description": "Ecom information about company's Target business",
        "tables": {
            "financial_reconciliation": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "orders": {"description": ""},
            "returns": {"description": ""},
            "returns_details": {"description": ""},
        },
    },
    "tiktok": {
        "dataset_description": "Ecom information about company's TikTok business",
        "tables": {
            "attribution_tiktok": {"description": ""},
            "campaign_metrics": {"description": ""},
            "gmv_max_metrics": {"description": ""},
            "orders": {"description": ""},
            "returns": {"description": ""},
            "sku_duplicates": {"description": ""},
            "states_dict": {"description": ""},
            "tiktok_fba_finder": {"description": ""},
            "tiktok_fin_view_bi": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "tiktok_fin_view_bi_2": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "tiktok_finance_report": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "tiktok_finance_report_2": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "tiktok_order_temp": {"description": ""},
            "tiktok_shipping": {"description": ""},
            "tiktok_shipping_cost": {"description": ""},
        },
    },
    "walmart": {
        "dataset_description": "Ecom information about company's Walmart business",
        "tables": {
            "inventory": {"description": ""},
            "inventory_wfs": {"description": ""},
            "legacy_payments": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "legacy_payments_tmp": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "orders": {"description": ""},
            "orders_total": {"description": ""},
            "payments": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "payments_tmp": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"],
            },
            "returns": {"description": ""},
            "summary": {"description": ""},
        },
    },
    "zenefits": {
        "dataset_description": "HR-related dataset, do not use",
        "tables": {
            "employments": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "out_off_office": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "people": {"description": "", "authorized_users": ["valerii@mellanni.com"]},
            "people_and_employments": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
        },
    },
}
