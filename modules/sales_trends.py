"""Resident pandas snapshot and bounded result cache for the sales trends page."""

from collections import OrderedDict
from pathlib import Path
from threading import RLock

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

NAMES = ("sales", "sessions", "ads", "forecast")
COLUMNS = {
    "sales": [
        "date", "asin", "collection", "size", "color", "units", "net_sales",
        "inventory_supply_at_fba", "available", "has_sales_row",
        "has_inventory_row", "change_notes",
    ],
    "sessions": ["date", "asin", "sessions"],
    "ads": [
        "date", "asin", "ad_spend", "impressions", "clicks", "total_units", "total_sales",
    ],
    "forecast": ["date", "asin", "forecast_units", "forecast_dollar"],
}


class SalesTrendsData:
    """Load source columns once; reuse calendar demand across date/filter changes."""

    def __init__(self, source, events, event_dates):
        self.events = events
        self.event_dates = list(event_dates)
        self.lock = RLock()
        self.cache = OrderedDict()
        if isinstance(source, (str, Path)):
            # BigQuery registers pandas' dbdate dtype, used by existing files.
            import db_dtypes  # noqa: F401
            frames = [
                pd.read_parquet(Path(source) / f"{name}.parquet", columns=COLUMNS[name])
                for name in NAMES
            ]
        else:
            frames = [frame.copy(deep=False) for frame in source]
        for frame in frames:
            frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
        sales, sessions, _, forecast = frames
        if "has_sales_row" not in sales:
            sales["has_sales_row"] = True
        observed = sales["has_sales_row"].fillna(False)
        if "has_inventory_row" in sales:
            observed = observed | sales["has_inventory_row"].fillna(False)
        dates = pd.concat([sales.loc[observed, "date"], sessions["date"]])
        self.coverage = (
            dates.min(), dates.max(), sessions["date"].min(), sessions["date"].max(),
        )
        self.date_bounds = (sales["date"].min().date(), sales["date"].max().date())
        self.frames = frames
        all_dates = pd.concat([sales["date"], sessions["date"], forecast["date"]])
        calendar = pd.date_range(all_dates.min(), all_dates.max() + pd.Timedelta(days=29))
        units = sales.loc[sales["asin"].notna(), ["date", "asin", "units"]].copy()
        units.loc[units["date"] > self.coverage[1], "units"] = np.nan
        grid = (
            units.pivot(index="date", columns="asin", values="units")
            .reindex(calendar)
            .astype(float)
        )
        coverage = (calendar >= self.coverage[0]) & (calendar <= self.coverage[1])
        grid.loc[coverage] = grid.loc[coverage].fillna(0)
        self.demand = {True: grid.rolling(30, min_periods=1).mean()}
        grid.loc[calendar.isin(pd.to_datetime(self.event_dates))] = np.nan
        self.demand[False] = grid.rolling(30, min_periods=1).mean()

    def _lookup(self, rows, keep_events):
        grid = self.demand[keep_events]
        dates = grid.index.get_indexer(rows["date"])
        asins = grid.columns.get_indexer(rows["asin"])
        valid = (dates >= 0) & (asins >= 0) & rows["asin"].notna().to_numpy()
        result = np.full(len(rows), np.nan)
        result[valid] = grid.to_numpy()[dates[valid], asins[valid]]
        return result

    def _query(
        self, target_asins, available_inv, include_events, date_range, periods, previous,
    ):
        return _filtered_sales(
            *self.frames, target_asins, available_inv, include_events,
            date_range, periods, previous, self.events,
            self.event_dates, self.coverage, self._lookup,
        )

    def query(
        self, target_asins, available_inv, include_events, date_range,
        periods="last year", previous=None, use_cache=True,
    ):
        previous = previous or (
            date_range[0] - relativedelta(years=1),
            date_range[1] - relativedelta(years=1),
        )
        key = (
            None if target_asins is None else tuple(sorted(target_asins)),
            available_inv, include_events, tuple(date_range), periods, tuple(previous),
        )
        # One shared immutable snapshot. Serialize working state and cache writes.
        with self.lock:
            if not use_cache or key not in self.cache:
                result = self._query(
                    target_asins, available_inv, include_events, date_range, periods, previous,
                )
                if not use_cache:
                    return result
                self.cache[key] = result
                while len(self.cache) > 16:
                    self.cache.popitem(last=False)
            self.cache.move_to_end(key)
            return tuple(frame.copy() for frame in self.cache[key])


def _filtered_sales(
    sales_df: pd.DataFrame,
    sessions_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    target_asins,
    available_inv,
    include_events,
    date_range,
    periods,
    previous,
    events,
    event_dates_list,
    coverage,
    demand_lookup,
):
    match periods:
        case "custom":
            prev_start, prev_end = previous

        case "last week":
            prev_start = date_range[0] - relativedelta(weeks=1)
            prev_end = date_range[1] - relativedelta(weeks=1)

        case p if p in events:
            prev_start, prev_end = previous

        case _:
            prev_start = date_range[0] - relativedelta(years=1)
            prev_end = date_range[1] - relativedelta(years=1)

    inv_column = "available" if available_inv else "inventory_supply_at_fba"
    history_start = min(prev_start, date_range[0]) - relativedelta(days=60)
    history_end = max(prev_end, date_range[1])
    calendar = pd.date_range(history_start, history_end, name="date")
    event_dates = pd.to_datetime(event_dates_list)

    sales_start, sales_end, sessions_start, sessions_end = coverage
    sales_coverage = (calendar >= sales_start) & (calendar <= sales_end)
    sessions_coverage = (calendar >= sessions_start) & (calendar <= sessions_end)

    sales_df, sessions_df, ads_df, forecast_df = (
        frame.loc[
            frame["date"].between(
                pd.Timestamp(history_start), pd.Timestamp(history_end)
            )
        ].copy()
        for frame in (sales_df, sessions_df, ads_df, forecast_df)
    )
    if target_asins is not None:
        sales_df = sales_df.loc[sales_df["asin"].isin(target_asins)]
        sessions_df = sessions_df.loc[sessions_df["asin"].isin(target_asins)]
        ads_df = ads_df.loc[ads_df["asin"].isin(target_asins)]

    # Notes and inventory-only rows must not expand the forecast universe.
    sales_asins = sales_df.loc[
        sales_df["has_sales_row"].fillna(False), "asin"
    ].unique()
    forecast_asins = forecast_df.loc[forecast_df["asin"].isin(sales_asins)]
    sales_df = pd.merge(
        sales_df, forecast_asins, how="outer", on=["date", "asin"], validate="1:1"
    ).sort_values(["asin", "date"])
    sales_df["change_notes"] = sales_df["change_notes"].fillna("")

    # Source queries return zero for inventory/notes-only rows. Future dates
    # still have no observed sales, even when a forecast or note exists.
    sales_df.loc[sales_df["date"] > sales_end, ["units", "net_sales"]] = float(
        "nan"
    )

    def summarize(keep_events):
        rows = sales_df.copy()
        excluded = (
            calendar.isin(event_dates) if not keep_events else calendar.isin([])
        )

        rows["asin_30d_avg"] = demand_lookup(rows, keep_events)
        demand = rows.groupby("date")["asin_30d_avg"].transform("sum")
        rows["asin_sales_share"] = rows["asin_30d_avg"].div(
            demand.where(demand > 0)
        )
        rows["stockout"] = (
            1
            - rows[inv_column]
            .div(rows["asin_30d_avg"].where(rows["asin_30d_avg"] > 0))
            .clip(0, 1)
        ) * rows["asin_sales_share"]
        rows.loc[
            (rows["asin_30d_avg"] == 0) & rows[inv_column].notna(), "stockout"
        ] = 0
        rows.loc[rows["date"] > sales_end, "stockout"] = float("nan")
        if not keep_events:
            rows = rows.loc[~rows["date"].isin(event_dates)]

        numeric_columns = [
            "units",
            "forecast_units",
            "forecast_dollar",
            "net_sales",
            "available",
            "inventory_supply_at_fba",
            "stockout",
        ]
        daily = (
            rows.groupby("date")[numeric_columns]
            .sum(min_count=1)
            .reindex(calendar)
        )
        daily["change_notes"] = (
            rows.groupby("date")["change_notes"]
            .agg(lambda notes: ", ".join(note for note in notes.unique() if note))
            .reindex(calendar, fill_value="")
        )
        daily["sessions"] = (
            sessions_df.groupby("date")["sessions"]
            .sum(min_count=1)
            .reindex(calendar)
        )
        # Keep traffic-only dates and actual zero-sale days. Future actuals
        # remain missing instead of being turned into forecast-period zeroes.
        daily.loc[sales_coverage, ["units", "net_sales"]] = daily.loc[
            sales_coverage, ["units", "net_sales"]
        ].fillna(0)
        daily.loc[sessions_coverage, "sessions"] = daily.loc[
            sessions_coverage, "sessions"
        ].fillna(0)
        daily.loc[excluded, numeric_columns + ["sessions"]] = float("nan")
        daily.loc[excluded, "change_notes"] = ""
        for source, name in (
            ("units", "30-day avg"),
            ("net_sales", "30-day sales avg"),
            ("sessions", "30-day sessions avg"),
        ):
            daily[name] = daily[source].rolling(30, min_periods=1).mean().round(1)
        daily["average selling price"] = daily["net_sales"].div(
            daily["units"].where(daily["units"] != 0)
        )
        # Preserve chart gaps for every series on excluded dates.
        daily.loc[excluded, daily.columns != "change_notes"] = float("nan")
        return rows, daily

    sales_visible, combined = summarize(include_events)
    previous = (
        summarize(True)[1]
        if periods in events and not include_events
        else combined
    )
    combined_previous = previous.loc[
        pd.Timestamp(prev_start) : pd.Timestamp(prev_end)
    ].copy()
    if not include_events and periods not in events:
        combined_previous = combined_previous.loc[
            ~combined_previous.index.isin(event_dates)
        ]
    combined_visible = combined.loc[
        pd.Timestamp(date_range[0]) : pd.Timestamp(date_range[1])
    ].copy()
    chart_columns = combined_visible.columns.difference(["change_notes"])
    combined_visible[chart_columns] = combined_visible[chart_columns].astype(
        float
    )

    selected = sales_visible["date"].between(
        pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    )
    asin_sales = (
        sales_visible.loc[selected]
        .groupby("asin")
        .agg(
            {
                "collection": "first",
                "size": "first",
                "color": "first",
                "units": "sum",
                "forecast_units": "sum",
                "forecast_dollar": "sum",
                "net_sales": "sum",
                "available": "last",
                "inventory_supply_at_fba": "last",
            }
        )
        .reset_index()
        .sort_values("net_sales", ascending=False)
    )
    selected_sessions = sessions_df.loc[
        sessions_df["date"].between(
            pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        )
    ]
    if not include_events:
        selected_sessions = selected_sessions.loc[
            ~selected_sessions["date"].isin(event_dates)
        ]
    asin_sessions = selected_sessions.groupby("asin", as_index=False)[
        "sessions"
    ].sum()
    asin_sales = pd.merge(
        asin_sales, asin_sessions, how="left", on="asin", validate="1:1"
    )
    total_sales = asin_sales["net_sales"].sum()
    asin_sales["sales_share"] = asin_sales["net_sales"] / (
        total_sales if total_sales != 0 else float("nan")
    )

    date_ads = ads_df.groupby("date")[
        [
            "ad_spend",
            "impressions",
            "clicks",
            "total_units",
            "total_sales",
        ]
    ].sum(min_count=1)
    ads_previous = date_ads.loc[
        pd.Timestamp(prev_start) : pd.Timestamp(prev_end)
    ].copy()
    ads_visible = date_ads.reindex(
        pd.date_range(date_range[0], date_range[1], name="date")
    )
    if not include_events:
        ads_visible.loc[ads_visible.index.isin(event_dates)] = float("nan")
        if periods not in events:
            ads_previous = ads_previous.loc[~ads_previous.index.isin(event_dates)]

    # Match the existing return contract: chart dates are timestamps; previous
    # period dates are datetime.date values.
    combined_previous = combined_previous.reset_index()
    combined_previous["date"] = combined_previous["date"].dt.date
    ads_previous = ads_previous.reset_index()
    ads_previous["date"] = ads_previous["date"].dt.date
    return (
        combined_visible.reset_index(),
        combined_previous,
        asin_sales,
        ads_visible.reset_index(),
        ads_previous,
    )
