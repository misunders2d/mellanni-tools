import keepa
import os
from numpy import nan
import pandas as pd
import streamlit as st
import time

KEEPA_KEY = os.getenv("KEEPA_KEY", "")


class KeepaProduct:
    api = keepa.Keepa(KEEPA_KEY, timeout=60)
    # create sales ranges (min - max)
    sales_tiers: dict = {
        -1: 0,
        0: 50,
        50: 100,
        100: 200,
        200: 300,
        300: 400,
        400: 500,
        500: 600,
        600: 700,
        700: 800,
        800: 900,
        900: 1000,
        1000: 2000,
        2000: 3000,
        3000: 4000,
        4000: 5000,
        5000: 6000,
        6000: 7000,
        7000: 8000,
        8000: 9000,
        9000: 10000,
        10000: 20000,
        20000: 30000,
        30000: 40000,
        40000: 50000,
        50000: 60000,
        60000: 70000,
        70000: 80000,
        80000: 90000,
        90000: 100000,
        100000: 150000,
    }

    def __init__(self, asin=None, domain="US"):
        self.exists: bool = False
        self.asin: str = input("ASIN?\n\n") if not asin else asin
        self.domain: str = domain
        self.title: str | None = None
        self.image: str | None = None
        self.data: list | None = None
        self.brand: str | None = None
        self.parent: str | None = None
        self.pivot: pd.DataFrame | None = None
        self.initial_days: int = 360
        self.variations = set()
        self.avg_price = 0

    def __ge__(self, other):
        return self.max_sales >= other.max_sales

    def __le__(self, other):
        return self.max_sales <= other.max_sales

    def __gt__(self, other):
        return self.max_sales > other.max_sales

    def __lt__(self, other):
        return self.max_sales < other.max_sales

    def __eq__(self, other):
        return self.max_sales == other.max_sales

    def __str__(self, days=30):
        self.get_last_days(days=days)
        if not self.exists:
            return f"{self.asin} does not exist or there is no Keepa data for it"
        return f"{self.asin}: {self.brand}\n{self.title}\nLatest {days} days sales: {self.min_sales:,.0f} - {self.max_sales:,.0f} units ({self.avg_sales:,.0f} average)\nAverage price last {days} days: \$ {self.avg_price:.2f}, total sales: \$ {(self.avg_sales*self.avg_price):,.0f}"

    def _format_numbers(self, df):
        if "full price" in df.columns:
            df["full price"] = round(df["full price"], 2)
        if "final price" in df.columns:
            df["final price"] = round(df["final price"], 2)
        if "sales max" in df.columns:
            df["sales max"] = df.loc[~df["sales max"].isnull(), "sales max"].astype(int)
        if "sales min" in df.columns:
            df["sales min"] = df.loc[~df["sales min"].isnull(), "sales min"].astype(int)
        if "LD" in df.columns:
            df["LD"] = round(df["LD"], 2)
        return df

    def query(self):
        if not self.data:
            try:
                self.data = KeepaProduct.api.query(self.asin, domain=self.domain)
            except Exception:
                self.data = [{}]

    def extract_from_products(self, products: list):
        self.data = [x for x in products if x["asin"] == self.asin]

    def convert_time(self, keepa_time: int) -> pd.Timestamp | str:
        """function that converts time from keepa format to datetime format"""
        if keepa_time == 0:
            return "unknown"
        converted = (keepa_time + 21564000) * 60000
        converted = pd.to_datetime(converted, unit="ms")
        return converted

    def apply_sales_tiers(self, x):
        """map minimal sales tiers to sales tiers dict to get min-max sales"""
        if x == -1:
            return 0
        return KeepaProduct.sales_tiers.get(x, x * 1.3)

    def get_variations(self):
        if not self.data:
            self.query()
        if (
            self.data
            and "variations" in self.data[0].keys()
            and self.data[0]["variations"]
        ):
            self.variations.update([x["asin"] for x in self.data[0]["variations"]])
            self.variation_theme_dict = [
                theme["attributes"]
                for theme in self.data[0]["variations"]
                if theme["asin"] == self.asin
            ][0]
            self.variation_theme = {
                x["dimension"]: x["value"] for x in self.variation_theme_dict
            }

    def pull_sales(self):
        if not self.data:
            self.query()
        elif self.data == "Not found":
            return
        self.title = self.data[0].get("title")
        img_links = self.data[0].get("imagesCSV")
        if img_links and len(img_links.split(",")) > 0:
            self.image = (
                "https://m.media-amazon.com/images/I/" + img_links.split(",")[0]
            )
        self.brand = self.data[0].get("brand")
        self.parent = self.data[0].get("parentAsin")
        sales = self.data[0].get("data", {}).get("df_NEW", pd.DataFrame())
        if len(sales) > 0:
            self.exists = True
        else:
            return
        sales = sales.rename(columns={"value": "full price"}).fillna(-1)
        self.last_sales_date = sales.index[-1]
        return sales

    def pull_coupons(self):
        sales = self.pull_sales()
        if not self.exists:
            return
        coupons = self.data[0].get("couponHistory")
        if coupons:
            times = [self.convert_time(x) for x in coupons[::3]]
            discounts = coupons[1::3]
            perc_off = [
                x if x < 0 else 0 for x in discounts
            ]  # separate % off discounts
            money_off = [
                x / 100 if x > 0 else 0 for x in discounts
            ]  # separate $ off discounts
            sns_coupons = coupons[2::3]
            sns_perc_off = [
                x if x < 0 else 0 for x in sns_coupons
            ]  # separate % off sns
            sns_money_off = [
                x / 100 if x > 0 else 0 for x in sns_coupons
            ]  # separate $ off sns

            coupon_history = pd.DataFrame(
                data=list(zip(perc_off, money_off, sns_perc_off, sns_money_off)),
                index=times,
                columns=["% off", "$ off", "SNS %", "SNS $"],
            )
        else:
            coupon_history = pd.DataFrame(
                [[0, 0, 0, 0]],
                index=[self.last_sales_date],
                columns=["% off", "$ off", "SNS %", "SNS $"],
            )

        sales_history = pd.merge(
            sales, coupon_history, how="outer", left_index=True, right_index=True
        ).ffill()
        return sales_history

    def pull_lds(self):
        sales_history = self.pull_coupons()
        if not self.exists:
            return
        lds = (
            self.data[0]
            .get("data", {})
            .get(
                "df_LIGHTNING_DEAL",
                pd.DataFrame([0], index=[self.last_sales_date], columns=["LD"]),
            )
        )
        lds = lds.fillna(0)
        lds = lds.rename(columns={"value": "LD"})

        sales_history = (
            pd.merge(sales_history, lds, how="outer", left_index=True, right_index=True)
            .ffill()
            .fillna(0)
        )
        return sales_history

    def pull_bsr(self):
        sales_history = self.pull_lds()
        if not self.exists:
            return
        bsr = (
            self.data[0]
            .get("data", {})
            .get(
                "df_SALES",
                pd.DataFrame([nan], index=[self.last_sales_date], columns=["BSR"]),
            )
            .replace(-1, nan)
        )
        bsr = bsr.rename(columns={"value": "BSR"})
        sales_history = pd.merge(
            sales_history, bsr, how="outer", left_index=True, right_index=True
        ).ffill()
        sales_history["final price"] = (
            (
                sales_history["full price"]
                - sales_history["$ off"]
                - sales_history["SNS $"]
            )
            * (1 + sales_history["% off"] / 100)
            * (1 + sales_history["SNS %"] / 100)
        )

        sales_history.loc[sales_history["LD"] != 0, "final price"] = sales_history["LD"]
        return sales_history

    def pull_monthly_sold(self):
        sales_history = self.pull_bsr()
        if not self.exists:
            return
        monthly_sold = self.data[0].get("monthlySoldHistory")
        if monthly_sold:
            times = [self.convert_time(x) for x in monthly_sold[::2]]
            monthly_units = monthly_sold[1::2]
            monthly_sold_history = pd.DataFrame(
                data=monthly_units, index=times, columns=["monthlySoldMin"]
            )
        else:
            monthly_sold_history = pd.DataFrame(
                [-1], index=[self.last_sales_date], columns=["monthlySoldMin"]
            )
        monthly_sold_history["monthlySoldMax"] = monthly_sold_history[
            "monthlySoldMin"
        ].map(self.apply_sales_tiers)
        monthly_sold_history = monthly_sold_history.replace(-1, 0)

        self.sales_history_monthly = pd.merge(
            sales_history,
            monthly_sold_history,
            how="outer",
            left_index=True,
            right_index=True,
        ).ffill()
        return self.sales_history_monthly

    def generate_daily_sales(self, days=360):
        self.short_history = self.pull_monthly_sold()
        if not self.exists:
            return
        self.short_history["sales min"] = self.short_history["monthlySoldMin"] / (
            60 * 24 * 30
        )
        self.short_history["sales max"] = self.short_history["monthlySoldMax"] / (
            60 * 24 * 30
        )

        # lifetime = pd.date_range(self.short_history.index.min(), self.short_history.index.max(), freq='min')
        lifetime = pd.date_range(
            (pd.to_datetime("today") - pd.Timedelta(days=days)).date(),
            self.short_history.index.max(),
            freq="min",
        )

        lifetime_df = pd.DataFrame(index=lifetime)
        minutely_history = pd.merge(
            lifetime_df,
            self.short_history,
            how="left",
            left_index=True,
            right_index=True,
        ).ffill()
        # remove price info with full price == -1 product blocked
        minutely_history.loc[minutely_history["full price"] == -1, "final price"] = nan
        minutely_history["full price"] = minutely_history["full price"].replace(-1, nan)

        # trim minutely history into short history
        self.short_history = minutely_history.copy()
        sum_cols = self.short_history.columns
        self.short_history["sum1"] = self.short_history[sum_cols].sum(axis=1)
        self.short_history["sum2"] = self.short_history[sum_cols].shift(-1).sum(axis=1)
        self.short_history["sum3"] = self.short_history[sum_cols].shift(1).sum(axis=1)

        self.short_history["diff"] = (
            self.short_history["sum1"] - self.short_history["sum2"]
        ) + (self.short_history["sum1"] - self.short_history["sum3"])
        self.short_history = self.short_history[self.short_history["diff"] != 0][
            sum_cols
        ]

        minutely_history["date"] = minutely_history.index.date
        self.pivot = minutely_history.pivot_table(
            values=[
                "full price",
                "% off",
                "$ off",
                "SNS %",
                "SNS $",
                "LD",
                "final price",
                "sales min",
                "sales max",
                "BSR",
            ],
            index="date",
            aggfunc={
                "full price": "mean",
                "% off": "min",
                "$ off": "min",
                "SNS %": "min",
                "SNS $": "min",
                "LD": "max",
                "final price": "mean",
                "sales min": "sum",
                "sales max": "sum",
                "BSR": "min",
            },
        )
        if "full price" not in self.pivot.columns:
            self.pivot["full price"] = nan
        if "sales min" not in self.pivot.columns:
            self.pivot["sales min"] = nan
        if "sales max" not in self.pivot.columns:
            self.pivot["sales max"] = nan

        self.short_history["LD"] = self.short_history["LD"].replace(0, nan)
        self.short_history["full price"] = self.short_history["full price"].replace(
            -1, nan
        )
        self.short_history["coupon"] = (
            (
                minutely_history["full price"]
                - minutely_history["$ off"]
                - minutely_history["SNS $"]
            )
            * (1 + minutely_history["% off"] / 100)
            * (1 + minutely_history["SNS %"] / 100)
        )
        self.short_history.loc[
            self.short_history["coupon"] == self.short_history["full price"], "coupon"
        ] = nan
        self.pivot = self._format_numbers(self.pivot)
        self.pivot = self.pivot.replace(0, nan)

    def generate_monthly_summary(self):
        if not self.data:
            self.generate_daily_sales(days=self.initial_days)
        if self.data and isinstance(self.pivot, pd.DataFrame):
            summary = self.pivot.copy()
            summary = summary[summary.index >= pd.to_datetime("2020-01-01").date()]
            summary["year-month"] = (
                pd.to_datetime(summary.index).year.astype(str)
                + "-"
                + pd.to_datetime(summary.index).month.astype(str).str.zfill(2)
            )
            self.summary = summary.pivot_table(
                values=["final price", "full price", "sales max", "sales min", "BSR"],
                index="year-month",
                aggfunc={
                    "final price": "mean",
                    "full price": "mean",
                    "sales max": "sum",
                    "sales min": "sum",
                    "BSR": "mean",
                },
            )
            self.summary[["final price", "full price"]] = self.summary[
                ["final price", "full price"]
            ].round(2)
            self.summary[["BSR", "sales max", "sales min"]] = self.summary[
                ["BSR", "sales max", "sales min"]
            ].round(0)

    def get_last_days(self, days=360):
        self.generate_daily_sales(days=days)
        if not self.exists:
            return
        if self.pivot is None:
            raise BaseException("self.pivot is not initialized")
        self.last_days = self.pivot[
            self.pivot.index
            >= (pd.to_datetime("today") - pd.Timedelta(days=days)).date()
        ]
        self.last_days["asin"] = self.asin
        self.min_sales = int(self.last_days["sales min"].sum())
        self.max_sales = int(self.last_days["sales max"].sum())
        self.avg_sales = (self.min_sales + self.max_sales) / 2
        self.full_price = self.last_days["full price"].mean()
        if "final price" in self.last_days.columns:
            self.avg_price = self.last_days["final price"].mean()


def get_products(asins: list, domain="US", update=None):
    api = keepa.Keepa(KEEPA_KEY, timeout=60)
    products = api.query(asins, domain=domain, update=update)
    return products


def get_tokens(api_key=KEEPA_KEY):
    api = keepa.Keepa(api_key, timeout=60)
    api.update_status()
    return api.tokens_left


def get_product_details(asins: list[str]):
    api = keepa.Keepa(KEEPA_KEY, timeout=60)
    tokens = api.tokens_left
    if tokens < len(asins):
        st.write("Please wait, not enough tokens to pull data from Amazon")
        time.sleep(20)
    products = api.query(asins)
    items = {}
    for p in products:
        asin = p.get("asin")
        brand = p.get("brand")
        items[asin] = {}
        title = p.get("title")
        bulletpoints = p.get("features", [])
        description = p.get("description")
        price = p.get("data", {}).get("df_NEW").dropna().iloc[-1].values[0]
        coupon = p.get("coupon")
        if not coupon:
            coupon = 0
        else:
            if coupon[0] < 0:
                coupon = round(price * coupon[0] / 100, 2)
            elif coupon[0] > 0:
                coupon = -coupon[0] / 100

        sales = p.get("monthlySold")
        if not sales:
            sales = 0

        img_link = (
            "https://m.media-amazon.com/images/I/"
            + p.get("imagesCSV", "").split(",")[0]
        )

        items[asin]["brand"] = brand
        items[asin]["title"] = title
        items[asin]["bulletpoints"] = "\n".join(bulletpoints)
        items[asin]["description"] = description
        items[asin]["full price"] = price
        items[asin]["discount"] = coupon
        items[asin]["monthly sales"] = sales
        items[asin]["image"] = img_link
    return items
