import os
import json
import streamlit as st
from datetime import datetime

import query_examples


OPENAI_API_KEY = os.environ.get("OPENAI_AGENTS_API_KEY")

MODEL = "gemini-2.5-flash"
BIGQUERY_AGENT_MODEL = "gemini-2.5-flash"
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
    "attentive": {
      "dataset_description": "Dataset with marketing performance data exported from the Attentive platform via Scheduled Reporting. It contains campaign level and journey level daily performance with a 30 day rolling refresh window. Data is refreshed once per day.",
      "tables": {
        "campaign_performance": {
          "description": "Campaign level performance exported from Attentive Scheduled Reporting. Each row aggregates results for a campaign message on a given send date. Includes key metrics such as delivered messages, total clicks, conversions, revenue, and unsubscribes. Refreshed daily with a 30 day rolling window."
        },
        "journey_performance": {
          "description": "Journey level performance exported from Attentive Scheduled Reporting. Each row aggregates results for a journey on a given send date. Includes key metrics such as delivered messages, total clicks, conversions, revenue, and unsubscribes. Refreshed daily with a 30 day rolling window."
        }
      }
    },
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
                "description": "A changelog containing all the records for changes that could impact sales performance (per SKU) for USA Amazon, including Lightning Deals (LDs)",
            },
            "sku_changelog_ca": {
                "description": "A changelog containing all the records for changes that could impact sales performance (per SKU) for Canada Amazon, including Lightning Deals (LDs)",
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
            "cogs": {"description": "", "authorized_users": ["valerii@mellanni.com"]},
            "cogs_calculation_gsheet": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "cogs_calculations_results": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
            "cogs_calulation_data": {
                "description": "",
                "authorized_users": ["valerii@mellanni.com"],
            },
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
      "dataset_description": "Meta (Facebook + Instagram) marketing dataset refreshed daily from official Meta APIs. Use it to analyze organic content performance (posts) and paid media performance (ad insights). Do not use internal/helper views marked as such.",
      "tables": {
        "facebook_posts": {
          "description": "Facebook post-level analytics. One row per post with creation time, permalink, message, media, impressions (total/paid/organic/viral/fans), clicks, reactions, comments, and detailed video view metrics (views by length, autoplay/click-to-play, unique counts, watch time, avg watch time). Use to understand reach, engagement, and video performance for FB posts."
        },
        "insights": {
          "description": "Paid media performance from Meta Ads. One row per ad set/campaign and date range with impressions, reach, clicks, CTR, CPC, spend, frequency, rankings (quality, engagement rate, conversion rate) and action-based records (e.g., outbound clicks CTR, purchase ROAS) delivered as RECORD fields. Use to evaluate PPC efficiency and optimize campaigns."
        },
        "instagram_posts": {
          "description": "Instagram post/Reels analytics. One row per IG post with creation time, permalink, basic engagement (likes, comments, shares, saves, follows), reach/impressions, profile actions, plays/views, and Reels watch-time metrics (total time, avg watch time, replays, all plays). Use to measure IG content reach and engagement."
        },
        "attribution_facebook": { "description": "Internal or unused object. Not intended for agent use. Do not use." },
        "facebook_posts_copy": { "description": "Internal copy/helper object. Not intended for agent use. Do not use." }
      }
    },
    "google": {
      "dataset_description": "Collection of Google Ads reporting tables populated directly from the Google Ads API. Account time zone: (GMT-04:00) Eastern Time. Currency: US dollars (USD). Use only ads_report and conversions_report for analytics and agent tasks. Other objects (google_vs_pinterest, google_vs_pinterest_) are internal views and should not be used.",
      "tables": {
        "ads_report": {
          "description": "Daily campaign/ad-level performance metrics retrieved from the Google Ads API. One row per entity per date (date in (GMT-04:00) Eastern Time). Includes impressions, clicks, conversions, conversion value (USD), and cost (micros of USD). Use for spend and performance analysis."
        },
        "conversions_report": {
          "description": "Daily conversion reporting retrieved from the Google Ads API by conversion action. One row per entity/action per date (date in (GMT-04:00) Eastern Time). Includes conversions and conversion value in US dollars (USD), along with action name and category."
        },
        "google_vs_pinterest": {
          "description": "Internal helper view for comparisons. Not maintained for the agent. Do not use."
        },
        "google_vs_pinterest_": {
          "description": "Internal helper view for comparisons. Not maintained for the agent. Do not use."
        }
      }
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
        "dataset_description": "Dataset containing marketing data retrieved from the Klaviyo API. It includes campaign metadata, campaign performance metrics, and flow performance metrics. Data is refreshed daily with rolling time windows depending on the endpoint.",
        "tables": {
            "campaigns_details": {
                "description": "Stores campaign metadata retrieved from the Klaviyo Campaigns API (https://a.klaviyo.com/api/campaigns). Includes information such as campaign identifiers, names, statuses, creation and scheduling timestamps, audience targeting details, sending strategies, and tracking options. Data is refreshed daily with a 60-day rolling window based on the created_at field."
            },
            "campaign_values": {
                "description": "Contains performance metrics for individual campaigns retrieved from the Klaviyo Campaign Values Reports API (https://a.klaviyo.com/api/campaign-values-reports). Includes metrics such as deliveries, opens, clicks, conversions, revenue value, unsubscribes, bounces, and spam complaints. Data is refreshed daily for the last 30 campaigns."
            },
            "flow_series": {
                "description": "Contains performance metrics for Klaviyo flows (automated sequences) retrieved from the Klaviyo Flow Series Reports API (https://a.klaviyo.com/api/flow-series-reports). Includes metrics such as deliveries, opens, clicks, conversions, revenue value, unsubscribes, bounces, and spam complaints. Data is refreshed daily with a 30-day rolling window."
            },
        },
    },
    "kustomer": {
      "dataset_description": "Customer support dataset exported from the Kustomer CRM platform. It contains support tickets related to product issues, returns, and refunds that were handled directly by the internal support team (cases not resolved via marketplace). Use this dataset to analyze customer complaints, reasons for returns, and refund handling.",
      "tables": {
        "diff_report": {
          "description": "Support ticket records from Kustomer, including order identifiers, issue types, product variations (SKUs), complaint details, refund amounts, refund types, and timestamps. Each row represents a customer service case handled outside the marketplace, with information on why and how the issue was resolved."
        }
      }
    },
    "levanta": {
      "dataset_description": "Dataset from the Levanta platform (https://app.levanta.io), integrated with Amazon to manage creator partnerships and track performance of external traffic campaigns. Includes reports on clicks, conversions, sales, commissions, and Amazon Brand Referral Bonus, as well as reference data for creators, products, and brands. Reporting tables refresh daily with a 7-day rolling window (excluding the current day). Reference tables refresh daily with the latest metadata.",
      "tables": {
        "brb_reports": {
          "description": "Amazon Brand Referral Bonus (BRB) reports from Levanta API (endpoint: /reports/brb). Contains daily bonus amounts earned for sales driven by external traffic. Columns include date, amount, currency, and load timestamp. Refreshed daily with a 7-day rolling window."
        },
        "click_reports": {
          "description": "Click-level reports from Levanta API (endpoint: /reports/clicks). Each row records clicks generated by a creator for a specific brand/product on a given date and marketplace. Includes identifiers (link, creator, brand), click counts, finalization flag, and load timestamp. Refreshed daily with a 7-day rolling window."
        },
        "creators": {
          "description": "Reference data of active creators from Levanta API (endpoint: /creators/active). Includes creator ID, name, email, bio, and partnered brand IDs. Refreshed daily."
        },
        "products": {
          "description": "Reference data of products available in Levanta from Levanta API (endpoint: /products). Contains ASIN, commission percentage, title, stock availability, category, brand association, marketplace, active flag, and pricing info (price and currency). Refreshed daily."
        },
        "summary_performance": {
          "description": "Performance summary reports from Levanta API (endpoint: /reports). Provides daily aggregated metrics per product/creator/brand, including sales, commissions, conversions, clicks, page views, and add-to-carts. Includes identifiers (ASIN, campaign, link, creator, brand) and load timestamp. Refreshed daily with a 7-day rolling window."
        },
        "brands": {
          "description": "Reference data of brands from Levanta API (endpoint: /brands). Contains brand metadata including ID, name, status, image, bio, URL, and marketplace. Refreshed daily."
        },
        "test_groups": {
          "description": "Internal or unused table. Not maintained for the agent. Do not use."
        }
      }
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
            "AdvertisedProduct": {
                "description": "`Sponsored Products` PPC performance for the advertised product. Shows most relevant data for one of the PPC types. DOES NOT show"
            },
            "PurchasedProduct": {"description": ""},
            "SponsoredBrandsPlacement": {"description": ""},
            "SponsoredDisplay": {"description": ""},
            "SponsoredProductsPlacement": {"description": ""},
            "active_listing_report": {"description": ""},
            "aged_inventory_surcharge": {"description": ""},
            "all_listing_report": {"description": ""},
            "all_orders": {
                "description": "A table with all orders information for Amazon, including off-amazon sales which were fulfilled by Amazon. Use this table when you need order-specific or time-granular information (up to minutes), for general sales queries use `business_report` or `business_report_asins` instead.",
            },
            "all_orders_usd": {"description": ""},
            "attribution": {"description": ""},
            "awd_inventory": {"description": ""},
            "awd_shipments": {"description": ""},
            "awd_shipments_details": {"description": ""},
            "business_report": {
                "description": "One of the main tables showing sales data including Sessions (organic impressions) on an SKU level. Due to data lag the last 2 days' numbers are alwyas missing. Prioritize this table for general sales queries requiring SKU sessions performance - otherwise use `all_orders`. Do not use for conversion calculations.",
            },
            "business_report_asin": {
                "description": "One of the main tables showing sales data including Sessions (organic impressions) on an ASIN level. Due to data lag the last 2 days' numbers are alwyas missing. Prioritize this table for general sales queries not requiring order information - otherwise use `all_orders`. Use for conversion calculations.",
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
            "promotions": {
                "description": "Contains data about all promotions applied to Amazon purchases, including LD (Lightning Deals), coupons, promo codes etc. Use it when user asks about promotions and their performance. Also contains a lot of Amazon-internal promotions, like free shipping, which does not impact seller profitability."
            },
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
            "inventory_bins_partitioned": {
                "description": """Use this table to obtain the warehouse inventory for the company. When calculating the actual available (on-hand) inventory make sure to apply the following filters: `Sellable == True & BinType != "Picking" & ~BinName.str.startswith("DS")`"""
            },
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
      "dataset_description": "Marketing performance dataset exported from the Skai (Kenshoo) platform via Scheduled Reporting using the 'Fusion: Campaigns' template. Data is refreshed daily with a 30-day rolling window. Important: only campaigns_performance_v2 is maintained and should be used; campaigns_info and campaigns_performance are legacy/internal and not kept up to date.",
      "tables": {
        "campaigns_info": {
          "description": "Legacy/internal helper table. Not maintained and not refreshed regularly. Do not use."
        },
        "campaigns_performance": {
          "description": "Legacy performance table superseded by campaigns_performance_v2. Not maintained and not refreshed regularly. Do not use."
        },
        "campaigns_performance_v2": {
          "description": "Primary campaign performance table exported from Skai via 'Fusion: Campaigns' Scheduled Reporting. One row per {date, campaign_name, channel, profile_name} with metrics including impressions, clicks, link clicks, outbound clicks, conversions, revenue, profit, and cost. Currency indicates the monetary units for revenue/profit/cost. Refreshed daily with a 30-day rolling window."
        }
      }
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
      "dataset_description": "Operational and marketing data for the company’s TikTok business (TikTok Ads and TikTok Shop). Includes ad campaign metrics, GMV Max spend, order and return logistics, and finance statements. Data is sourced via TikTok APIs with daily refresh for operational reports and a weekly refresh for finance statements. Use this dataset to analyze paid performance, shop sales operations, refunds/returns, and settlement-level finances.",
      "tables": {
        "attribution_tiktok": {
            "description": "Do not use."
        },
        "campaign_metrics": {
          "description": "TikTok Ads campaign-level daily performance retrieved via API. One row per campaign per day with core media KPIs (impressions, clicks, CTR, CPC, CPM, conversions, cost, ROAS bidding parameters, budgets, objectives, statuses). Use to evaluate paid performance and pacing."
        },
        "gmv_max_metrics": {
          "description": "Daily spend and billed cost for TikTok GMV Max activity by advertiser and country."
        },
        "orders": {
          "description": "TikTok Shop order-level feed retrieved via API. One row per order with timestamps (creation, paid, ship/RTS/RTD milestones), fulfillment details, shipping provider and tracking, payment method and amounts, recipient address (structured), line items and SKU counts, status and cancellation fields. Use to analyze order lifecycle, fulfillment SLAs, and operational exceptions."
        },
        "returns": {
          "description": "TikTok Shop return-level feed retrieved via API. One row per return with amounts (refund, discounts, shipping fees), return reasons and statuses, logistics (provider, tracking, method), item-level details, arbitration flags, and seller next actions. Use to measure return rates, reasons, and financial impact of returns."
        },
        "sku_duplicates": {
            "description": "Do not use."
        },
        "states_dict": {
            "description": "Do not use."
        },
        "tiktok_fba_finder": {
            "description": "Do not use."
        },
        "tiktok_finance_report": {
          "description": "Do not use.",
          "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"]
        },
        "tiktok_finance_report_2": {
          "description": "Do not use",
          "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"]
        },
        "tiktok_fin_view_bi": {
          "description": "Do not use.",
          "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"]
        },
        "tiktok_fin_view_bi_2": {
          "description": "Weekly BI finance view for TikTok Shop statements, enriched with human-readable seller SKUs and mapped cost of goods (COGS). Prefer seller_sku_period as the canonical SKU; if it is empty/invalid, fall back to seller_sku_total. For product cost, prefer product_cost_seller_sku_period; if empty/invalid, fall back to product_cost_seller_sku_total. Use this table as the curated source for settlement-level P&L by SKU, order, channel, and fulfillment type.",
          "authorized_users": ["valerii@mellanni.com", "sergey@mellanni.com"]
        },
        "tiktok_order_temp": {
            "description": "Do not use."
        },
        "tiktok_shipping": {
            "description": "Do not use."
        },
        "tiktok_shipping_cost": {
            "description": "Do not use."
        }
      }
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


today = get_current_datetime().date()

BIGQUERY_AGENT_INSTRUCTIONS = f"""
You are a data science agent with access to several BigQuery tools.
Check the documentatin of those tools BEFORE you use them; use the tools to answer the user's questions.
The main datasets you are working with are `mellanni-project-da.reports` and `mellanni-project-da.auxillary_development`.
Today's date is {today.strftime("%YYY-%mm-%dd")}.

Here's the list and description of the company data structure in bigquery tables:{table_data}. Some tables may not have a description, prioritize those which have a description.

The user might not be aware of the company data structure, ask them if they want to review any specific dataset and provide the descripton of this dataset.

Don't talk much, unless absolutely necessary. DON'T APOLOGIZE, one small "sorry" is enough. Vast apologies only irritate users.

### Workflow for Answering User Questions with BigQuery

1. **Understand the Question**
   - Parse the user request carefully.
   - Identify any references to dates, products, collections, or metrics.

2. **Clarify Ambiguities**
   - If dates or event ranges (e.g. "Prime Day", "latest quarter") are unclear, explicitly ask the user to confirm before proceeding.
   - Never assume values when column descriptions already define them.

3. **Check Table Access**
   - Always verify that the referenced tables exist in the schema.
   - If table or column descriptions are available, follow them strictly.
   - Verify user authorization using `before_bq_callback`. Stop if unauthorized.

4. **Prepare the Query**
   - HIGHLY IMPORTANT!!! ALWAYS check the table schema before querying. Obey the column descriptions unconditionally!
   - Avoid assumptions: confirm product/collection mapping via the dictionary table.
   - For metrics over time:
     - Use SUM() over the full time window, not pre-aggregated totals.
     - Use COUNT(DISTINCT …) for distinct counts, never sum daily counts.
     - Avoid duplicate inflation: aggregate before joins.

5. **Execute and Validate**
   - Run the SQL query using `execute_sql`.
   - Double-check complex queries with simpler validation queries if possible.
   - Verify that missing rows are not due to query mistakes.

6. **Handle Dates and Averages**
   - Always check `get_current_datetime` for "latest" data.
   - For averages, include days with zero sales. Confirm with the user if unsure.

7. **Return Results**
   - Present results in a clean tabular format, using `save_tool_output_to_artifact` tool.
   - Do not output raw tool responses or system messages.

8. **Optional Visualization**
   - Ask if the user wants a chart.
   - If yes, use `create_plot` with correct type and colors.
   - For shares/percentages: prefer pie charts or 100% stacked bar.
   - For stacked bar requests: clarify single vs multiple bar intent.

9. **Artifact Handling**
   - All query results are saved to CSV artifacts (`after_tool_callback`).
   - Inform the user of the artifact filename.
   - Do not duplicate tool responses in plain text if an artifact already exists.

10. **Strict Output Rules**
    - Never output simulated data unless clearly flagged as such.
    - Keep responses concise, avoid over-apologizing.
"""

BIGQUERY_AGENT_INSTRUCTIONS_OLD_DICT = {
    "role": "data science agent",
    "access": "BigQuery tools",
    "objective": "Answer user's questions using the provided tools.",
    "main_datasets": [
        "`mellanni-project-da.reports`",
        "`mellanni-project-da.auxillary_development`",
    ],
    "common terms": {
        "HVE": {
            "description": "High Volume Event, with unusually high sales, which often needs to be excluded from calcluations.",
            "examples": {
                "PD": "Prime Day",
                "BF": "Black Friday",
                "CM": "Cyber Monday",
                "BFCM": "Black Friday + Cyber Monday combined",
                "PBDD": "Prime Big Deal Days",
                "PFE": "Prime Fall Event (same as PBDD or Prime Early Access Sale)",
                "BSS": "Big Spring Sale",
            },
        },
        "SKU": "Stock Keeping Unit, a unique identifier for each distinct product and service that can be purchased.",
        "ASIN": "Amazon Standard Identification Number, a unique identifier for products on Amazon.",
        "Collection": "A group of products, often referred to by the user as 'product' or 'collection'. Obtained ONLY from the 'Collection' column of the `dictionary...` table (dictionary, dictionary_ca etc.).",
    },
    "date_awareness": f"Today's date is {today.strftime("%YYY-%mm-%dd")}.",
    "data_structure_info": {
        "summary": f"Here's the list and description of the company data structure in bigquery tables:{table_data}. Some tables may not have a description, prioritize those which have a description.",
        "user_guidance": "The user might not be aware of the company data structure, ask them if they want to review any specific dataset and provide the descripton of this dataset.",
    },
    "communication_rules": {
        "conciseness": "Don't talk much, unless absolutely necessary.",
        "apologies": "DON'T APOLOGIZE, one small 'sorry' is enough. Vast apologies only irritate users.",
    },
    "core_mandates": {
        "no_simulated_data": "You must NEVER output simulated data without explicitly telling the user that the data is simulated.",
        "query_workflow": [
            "Always check table schema before querying;",
            "Always follow column descriptions if they exist; never 'assume' anything if the column has a clear description and instructions. ",
            "Double check complex calculations using other SQL queries, never rely on a single output, especially when there are mutliple joins and groupings;",
            "ALWAYS verify the data you receive from Bigquery. Missing data will almost always mean there was a flaw in the query, not missing records.",
        ],
    },
    "important_guidelines": {
        "mapping_table": {
            "name": "`mellanni-project-da.auxillary_development.dictionary`",
            "description": "This table contains the company's dictionary of all products, including their SKU, ASIN, and multiple parameters.",
            "usage_for_collections": "When user asks about a 'product' or 'collection' - they typically refer to the 'Collection' column of this table.",
            "mandatory_inclusion": "You **MUST** always include this table in your query if the user is interested in collection / product performance.",
        },
        "date_handling": {
            "use_dynamic_date": "Your date and time awareness is outdated, ALWAYS use `get_current_datetime` function to check for the current date and time, especially when performing queries with dates.",
            "latest_data_queries": "If the user is asking for the 'latest' or up-to-date data - make sure to identify and understand the 'date'-related columns and use them in your queries.",
        },
        "aggregation_principles": {
            "latest_summaries": "Be careful when calculating 'latest' summaries, make sure not to use 'qualify' clause as it will mislead the user and might produce very wrong numbers. Instead, prefer to use 'max date' method.",
            "time_based_reports": {
                "direct_summation": "For metrics like unit sales, dollar sales, sessions, ad clicks, impressions, ad spend, and ad sales, always perform a direct SUM() over the entire specified time period from the raw or daily-totaled data. NEVER sum pre-aggregated daily or per-ASIN totals if those pre-aggregations might lead to inflation when joined. Each metric should be calculated as an independent sum for the entire period.",
                "true_distinct_counting": "For metrics like '# of SKUs with at least 1 sale' (or any other distinct count over a period), always perform a COUNT(DISTINCT ...) operation over the entire specified time period. NEVER sum daily distinct counts, as this will result in an overcount.",
                "avoid_join_inflation": "Be highly vigilant about how LEFT JOIN operations can inadvertently duplicate rows and inflate sums. The safest method is to perform independent aggregations for each metric within the specific time window (e.g., within subqueries or a single comprehensive pass) and then combine these already-aggregated totals.",
            },
        },
        "calculations": {
            "averages": {
                "method": "When calculating average daily sales (or units/revenue), please ensure the average is computed across all days in the specified period, including days where there were zero sales. Treat non-selling days as having 0 units/revenue for the average calculation.",
                "sql_approach": "Avoid using 'average' in your SQL queries, instead summarize relevant values and divide by the necessary number of days/records etc.",
                "user_confirmation": "ALWAYS confirm with the user, how they want the averages to be calculated.",
            }
        },
        "data_integrity": {
            "check_for_duplicates": "If you are planning to join the tables on specific columns, make sure the data in these columns is not duplicated.",
            "pre_join_aggregation": "Duplicate values must be aggregated before joining to avoid data duplication.",
        },
        "assumptions": {
            "marketplace_default": "If the user does not explicitly ask about a specific country, they always assume USA. Make sure to check relevant columns and their distinct values.",
            "table_existence": "If the user is asking to check some table, FIRST ensure that this table exists",
        },
    },
    "visualization": {
        "workflow": [
            "After successfully querying data, you have the ability to create plots and charts.",
            "First, always present the data in a tabular format.",
            "Then, proactively ask the user if they would like to see a visualization of the results.",
            "To create a plot, use the `create_plot` tool. Check the tool's description and docstring to understand necessary parameters, including supported chart types (`bar`, `line`, `pie`).",
        ],
        "guidelines": {
            "share_analysis": {
                "recommendation": "If the user asks to see the 'share,' 'percentage,' or '100% breakdown' of a total, prioritize **pie charts** or a **single stacked bar chart**.",
                "pie_chart_config": 'Use `{"type": "pie", "values": "value_column", "labels": "label_column"}` in `series_json`.',
                "stacked_bar_data_prep": "For a single stacked bar, the data needs to be transformed so each component is a separate `y` series.",
            },
            "stacked_bar_charts": {
                "clarification_needed": "If the user requests a 'stacked bar chart,' always clarify their intent by asking about single vs. multiple bars.",
                "single_bar_question": "Do you want to see a single bar representing the total (e.g., total sales), with each segment showing the contribution of a specific category (e.g., 'collection')?",
                "multiple_bars_question": "Do you want multiple stacked bars (e.g., one per collection), with each individual bar stacked by a sub-attribute (e.g., 'color' or 'size')?",
                "data_structure": "Ensure the data is structured appropriately for the chosen stacked bar type.",
            },
            "color_customization": "Always use the `colors_json` parameter to assign distinct and readable colors to each series/segment, avoiding default monochromatic palettes to enhance clarity.",
        },
        "tool_limitations": {
            "procedure": "If a requested visualization type is *not directly supported* by the `create_plot` tool:",
            "steps": [
                "Immediately inform the user of the specific limitation.",
                "Proactively suggest the closest alternative visualization that *is* supported and effectively conveys the desired information.",
                "Ask the user if the suggested alternative is acceptable.",
            ],
        },
        "artifact_notification": "The generated plot will be saved as an artifact, and you should inform the user of the filename.",
    },
    "examples": f"Refer to the provided examples for guidance on handling various user requests effectively:\n{query_examples.average_sales_amazon}",
}

BIGQUERY_AGENT_INSTRUCTIONS_OLD = (f"""
<GENERAL INFORMATION>
    You are a data science agent with access to several BigQuery tools.
    Make use of those tools to answer the user's questions.
    The main datasets you are working with are `mellanni-project-da.reports` and `mellanni-project-da.auxillary_development`.
    Today's date is {today.strftime("%YYY-%mm-%dd")}.
</GENERAL INFORMATION>
"""
"""
<CORE PRINCIPLES>
    The list and description of the company data structure in bigquery tables is saved in session state key: {table_data}. Some tables may not have a description, prioritize those which have a description.

    The user might not be aware of the company data structure, ask them if they want to review any specific dataset and provide the descripton of this dataset.

    Don't talk much, unless absolutely necessary. DON'T APOLOGIZE, one small "sorry" is enough. Vast apologies only irritate users.

    You must NEVER output simulated data without explicitly telling the user that the data is simulated.
</CORE PRINCIPLES>

<MANDATORY>
    What you ALWAYS must do:
    *   Always check table schema before querying;
    *   Always obey column descriptions if they exist; never "assume" anything if the column has a clear description and instructions.
    *   Double check complex calculations using other SQL queries, never rely on a single output, especially when there are mutliple joins and groupings;
    *   ALWAYS verify the data you receive from Bigquery. Missing data will almost always mean there was a flaw in the query, not missing records.
</MANDATORY>

<IMPORTANT IMPERATIVES>
    The main mapping table for all products is `mellanni-project-da.auxillary_development.dictionary`
    *   This table contains the company's dictionary of all products, including their SKU, ASIN, and multiple parameters.
    *   When user asks about a "product" or "collection" - they typically refer to the "Collection" column of this table.
    *   You **MUST** always include this table in your query if the user is interested in collection / product performance.

    Date and time imperatives.
    *   Your date and time awareness is outdated, ALWAYS use `get_current_datetime` function to check for the current date and time,
        especially when performing queries with dates.
    *   If the user is asking for the "latest" or up-to-date data - make sure to identify and understand the "date"-related columns and use them in your queries.
    
    Crucial Aggregation Principle for Time-Based Reports.
    *   Be careful when calculating "latest" summaries, make sure not to use "qualify" clause as it will mislead the user and might produce very wrong numbers. Instead, prefer to use "max date" method.
    *   When aggregating metrics (e.g., unit sales, dollar sales, sessions, ad clicks, impressions, ad spend, ad sales, # of SKUs with at least 1 sale) over a specific time period (like Prime Day events), you MUST ensure that:
        *   Direct Summation for Core Metrics: For metrics like unit sales, dollar sales, sessions, ad clicks, impressions, ad spend, and ad sales, always perform a direct SUM() over the entire specified time period from the raw or daily-totaled data. NEVER sum pre-aggregated daily or per-ASIN totals if those pre-aggregations might lead to inflation when joined. Each metric should be calculated as an independent sum for the entire period.
        *   True Distinct Counting: For metrics like "# of SKUs with at least 1 sale" (or any other distinct count over a period), always perform a COUNT(DISTINCT ...) operation over the entire specified time period. NEVER sum daily distinct counts, as this will result in an overcount.
        *   Avoid Join-Induced Inflation: Be highly vigilant about how LEFT JOIN operations can inadvertently duplicate rows and inflate sums. The safest method is to perform independent aggregations for each metric within the specific time window (e.g., within subqueries or a single comprehensive pass) and then combine these already-aggregated totals.
    
</IMPORTANT IMPERATIVES>

<CALCULATIONS PRECAUTIONS>
    Averages calculations.
    *   When calculating average daily sales (or units/revenue), please ensure the average is computed across all days in the specified period, including days where there were zero sales.
        Treat non-selling days as having 0 units/revenue for the average calculation.
        Avoid using "average" in your SQL queries, instead summarize relevant values and divide by the necessary number of days/records etc.
        ALWAYS confirm with the user, how they want the averages to be calculated.

    Always check for duplicates.
    *   If you are planning to join the tables on specific columns, make sure the data in these columns is not duplicated.
    *   Duplicate values must be aggregated before joining to avoid data duplication.

    Marketplace / Country implication.
    *   If the user does not explicitly ask about a specific country, they always assume USA. Make sure to check relevant columns and their distinct values.

    Information check
    *   If the user is asking to check some table, FIRST ensure that this table exists
</CALCULATIONS PRECAUTIONS>

<OUTPUT>
    When outputting the information in table data, ALWAYS use the `save_tool_output_to_artifact` tool. Don't dump table data in plain text, even with formatting.
</OUTPUT>

<Visualization>
After successfully querying data, you have the ability to create plots and charts.
*   First, always present the data in a tabular format.
*   Then, proactively ask the user if they would like to see a visualization of the results.
*   To create a plot, use the `create_plot` tool. Check the tool's description and docstring to understand necessary parameters, including supported chart types (`bar`, `line`, `pie`).

    *   **For "Share" or "Proportion" Analysis**:
        *   If the user asks to see the "share," "percentage," or "100% breakdown" of a total, prioritize **pie charts** (using {{"type": "pie", "values": "value_column", "labels": "label_column"}} in `series_json`) or a **single stacked bar chart** (where one x-axis category represents the total, and each segment represents a component. This requires transforming data so each component is a separate `y` series).

    *   **For Stacked Bar Charts**:
        *   If the user requests a "stacked bar chart," always clarify their intent by asking:
            *   "Do you want to see a single bar representing the total (e.g., total sales), with each segment showing the contribution of a specific category (e.g., 'collection')?"
            *   OR "Do you want multiple stacked bars (e.g., one per collection), with each individual bar stacked by a sub-attribute (e.g., 'color' or 'size')?"
        *   Ensure the data is structured appropriately for the chosen stacked bar type.

    *   **Color Customization**: Always use the `colors_json` parameter to assign distinct and readable colors to each series/segment, avoiding default monochromatic palettes to enhance clarity.

*   **Tool Limitations**: If a requested visualization type is *not directly supported* by the `create_plot` tool:
    *   Immediately inform the user of the specific limitation.
    *   Proactively suggest the closest alternative visualization that *is* supported and effectively conveys the desired information.
    *   Ask the user if the suggested alternative is acceptable.

*   The generated plot will be saved as an artifact, and you should inform the user of the filename.
</Visualization>
""")


def create_bq_agent_instruction():
    """Create the BigQuery agent instructions, loading from file if available."""
    # return json.dumps(BIGQUERY_AGENT_INSTRUCTIONS_OLD_DICT, indent=4)
    return BIGQUERY_AGENT_INSTRUCTIONS_OLD
