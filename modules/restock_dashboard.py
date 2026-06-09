from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Collection

import numpy as np
import pandas as pd
from google.cloud import bigquery


DEFAULT_LONG_TERM_DAYS = 180
DEFAULT_SHORT_TERM_DAYS = 14
DEFAULT_HISTORY_DAYS = 30
DEFAULT_PROJECTION_DAYS = 30
DEFAULT_ALERT_DAYS = 21


@dataclass(frozen=True)
class RestockConfig:
    top_n: int = 20
    long_term_days: int = DEFAULT_LONG_TERM_DAYS
    short_term_days: int = DEFAULT_SHORT_TERM_DAYS
    history_days: int = DEFAULT_HISTORY_DAYS
    projection_days: int = DEFAULT_PROJECTION_DAYS
    alert_days: int = DEFAULT_ALERT_DAYS
    include_events: bool = False


SUMMARY_COLUMNS = [
    "asin",
    "collection",
    "sub_collection",
    "short_title",
    "sku_count",
    "skus",
    "avg_units",
    "avg_dollars",
    "avg_units_short",
    "avg_units_long",
    "avg_dollars_short",
    "avg_dollars_long",
    "isr",
    "isr_short",
    "available",
    "fba_inventory",
    "inbound_shipped",
    "total_inventory",
    "days_to_stockout",
    "stockout_date",
    "projected_inventory_30d",
    "alert",
]


def get_last_non_event_days(
    num_days: int,
    max_date: date,
    include_events: bool = False,
    events: Iterable[date] | None = None,
) -> list[date]:
    """Match restock_2025 behavior: last N calendar days, excluding known event days by default."""
    if num_days <= 0:
        return []

    event_set = set(events or [])
    days: list[date] = []
    cursor = max_date
    while len(days) < num_days:
        if include_events or cursor not in event_set:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return sorted(days)


def calculate_inventory_isr(
    inventory: pd.DataFrame,
    inv_max_date_input: str | date | None = None,
    col_to_use: str = "asin",
) -> pd.DataFrame:
    """Calculate long/short in-stock-rate using FBA supply > 0, ported from restock_2025."""
    if inventory.empty:
        return pd.DataFrame(columns=[col_to_use, "ISR", "ISR_short"])

    required = {"date", col_to_use, "amz_inventory"}
    missing = required - set(inventory.columns)
    if missing:
        raise ValueError(f"inventory missing columns: {sorted(missing)}")

    df = inventory.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    inv_max_date = (
        pd.to_datetime(inv_max_date_input).date()
        if inv_max_date_input is not None
        else df["date"].max()
    )

    grouped = df.groupby(["date", col_to_use], as_index=False)["amz_inventory"].sum()
    grouped = grouped[grouped["date"] <= inv_max_date]
    grouped["in_stock_rate"] = grouped["amz_inventory"] > 0

    short_window = grouped[
        pd.to_datetime(grouped["date"]) >= pd.to_datetime(inv_max_date) - pd.Timedelta(days=13)
    ]

    long_isr = (
        grouped.pivot_table(values="in_stock_rate", index=col_to_use, aggfunc="mean")
        .round(2)
        .reset_index()
        .rename(columns={"in_stock_rate": "ISR"})
    )
    short_isr = (
        short_window.pivot_table(values="in_stock_rate", index=col_to_use, aggfunc="mean")
        .round(2)
        .reset_index()
        .rename(columns={"in_stock_rate": "ISR_short"})
    )
    return pd.merge(long_isr, short_isr, on=col_to_use, how="outer", validate="1:1").fillna(0)


def calculate_smart_asin_sales(
    sales: pd.DataFrame,
    asin_isr: pd.DataFrame,
    include_events: bool = False,
    sales_max_date_input: str | date | None = None,
    long_term_days: int = DEFAULT_LONG_TERM_DAYS,
    short_term_days: int = DEFAULT_SHORT_TERM_DAYS,
    events: Iterable[date] | None = None,
) -> pd.DataFrame:
    """Calculate smart ASIN velocity: ISR-adjusted short/long avg with restock_2025 weights."""
    if sales.empty:
        return pd.DataFrame(
            columns=[
                "asin",
                "ISR",
                "ISR_short",
                f"avg sales dollar, {short_term_days} days",
                f"avg sales units, {short_term_days} days",
                f"avg sales dollar, {long_term_days} days",
                f"avg sales units, {long_term_days} days",
                "avg units",
                "avg $",
            ]
        )

    required = {"date", "asin", "unit_sales", "dollar_sales"}
    missing = required - set(sales.columns)
    if missing:
        raise ValueError(f"sales missing columns: {sorted(missing)}")

    df = sales.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    sales_max_date = (
        pd.to_datetime(sales_max_date_input).date()
        if sales_max_date_input is not None
        else (pd.to_datetime(df["date"].max()) - pd.Timedelta(days=1)).date()
    )

    long_days = get_last_non_event_days(long_term_days, sales_max_date, include_events, events=events)
    short_days = get_last_non_event_days(short_term_days, sales_max_date, include_events, events=events)

    long_df = df[df["date"].isin(long_days)].fillna(0)
    short_df = long_df[long_df["date"].isin(short_days)]

    long_sales = (
        long_df.groupby("asin", as_index=False)
        .agg({"unit_sales": "sum", "dollar_sales": "sum"})
        .fillna(0)
    )
    short_sales = (
        short_df.groupby("asin", as_index=False)
        .agg({"unit_sales": "sum", "dollar_sales": "sum"})
        .fillna(0)
    )

    long_sales = pd.merge(long_sales, asin_isr, on="asin", how="left", validate="1:1").fillna(0)
    short_sales = pd.merge(short_sales, asin_isr, on="asin", how="left", validate="1:1").fillna(0)

    long_units_col = f"avg sales units, {long_term_days} days"
    long_dollars_col = f"avg sales dollar, {long_term_days} days"
    short_units_col = f"avg sales units, {short_term_days} days"
    short_dollars_col = f"avg sales dollar, {short_term_days} days"

    long_sales[long_dollars_col] = (
        long_sales["dollar_sales"] / long_term_days / long_sales["ISR"].replace(0, np.nan)
    ).round(2)
    long_sales[long_units_col] = (
        long_sales["unit_sales"] / long_term_days / long_sales["ISR"].replace(0, np.nan)
    ).round(2)
    short_sales[short_dollars_col] = (
        short_sales["dollar_sales"] / short_term_days / short_sales["ISR_short"].replace(0, np.nan)
    ).round(2)
    short_sales[short_units_col] = (
        short_sales["unit_sales"] / short_term_days / short_sales["ISR_short"].replace(0, np.nan)
    ).round(2)

    total = pd.merge(
        short_sales[["asin", "ISR", "ISR_short", short_dollars_col, short_units_col]],
        long_sales[["asin", long_dollars_col, long_units_col]],
        on="asin",
        how="outer",
        validate="1:1",
    ).fillna(0)

    total["avg units"] = ((0.6 * total[short_units_col]) + (0.4 * total[long_units_col])).round(4)
    total["avg $"] = ((0.6 * total[short_dollars_col]) + (0.4 * total[long_dollars_col])).round(2)

    spike_mask = (total[short_units_col] / total[long_units_col].replace(0, np.nan)) > 5
    total.loc[spike_mask, "avg units"] = (
        (0.1 * total.loc[spike_mask, short_units_col])
        + (0.9 * total.loc[spike_mask, long_units_col])
    ).round(4)
    total.loc[spike_mask, "avg $"] = (
        (0.1 * total.loc[spike_mask, short_dollars_col])
        + (0.9 * total.loc[spike_mask, long_dollars_col])
    ).round(2)

    return total.replace([np.inf, -np.inf], 0).fillna(0)


def normalize_dictionary(dictionary: pd.DataFrame) -> pd.DataFrame:
    needed = ["sku", "asin", "collection", "sub_collection", "short_title"]
    cols = [c for c in needed if c in dictionary.columns]
    df = dictionary.loc[:, cols].copy()
    for col in needed:
        if col not in df.columns:
            df[col] = ""
    for col in ["sku", "asin"]:
        df[col] = df[col].astype(str).str.strip()
    df = df[(df["sku"] != "") & (df["asin"] != "")]
    return df.drop_duplicates("sku")


def aggregate_inventory_history(inventory: pd.DataFrame) -> pd.DataFrame:
    """ASIN-level daily inventory history. total = Amazon Total FBA supply."""
    if inventory.empty:
        return pd.DataFrame(
            columns=["date", "asin", "available", "fba_inventory", "inbound_shipped", "total_inventory"]
        )

    df = inventory.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for col in ["available", "fba_inventory", "inbound_shipped"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    grouped = (
        df.groupby(["date", "asin"], as_index=False)
        .agg({"available": "sum", "fba_inventory": "sum", "inbound_shipped": "sum"})
        .sort_values(["asin", "date"])
    )
    # `Inventory_Supply_at_FBA` is Amazon's Total FBA supply: available +
    # inbound shipped + FC transfer-style reserved supply, excluding customer orders.
    # Do not add `inbound_shipped` again or projections double-count shipped units.
    grouped["total_inventory"] = grouped["fba_inventory"]
    return grouped


def normalize_sp_inventory_report(report: pd.DataFrame, snapshot_date: str | date | None = None) -> pd.DataFrame:
    """Normalize GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA rows to dashboard schema."""
    if report.empty:
        return pd.DataFrame(columns=["date", "sku", "asin", "available", "fba_inventory", "inbound_shipped", "total_inventory"])

    df = report.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "afn-listing-exists" in df.columns:
        df = df[df["afn-listing-exists"].astype(str).str.upper().eq("YES")].copy()
    required = {"sku", "asin", "afn-fulfillable-quantity", "afn-total-quantity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"SP inventory report missing columns: {sorted(missing)}")

    out = pd.DataFrame()
    out["sku"] = df["sku"].astype(str).str.strip()
    out["asin"] = df["asin"].astype(str).str.strip()
    out["date"] = pd.to_datetime(snapshot_date or date.today()).date()
    out["available"] = pd.to_numeric(df["afn-fulfillable-quantity"], errors="coerce").fillna(0)
    out["fba_inventory"] = pd.to_numeric(df["afn-total-quantity"], errors="coerce").fillna(0)
    out["inbound_shipped"] = (
        pd.to_numeric(df["afn-inbound-shipped-quantity"], errors="coerce").fillna(0)
        if "afn-inbound-shipped-quantity" in df.columns
        else 0
    )
    out["total_inventory"] = out["fba_inventory"]
    out = out[(out["sku"] != "") & (out["sku"].str.lower() != "nan") & (out["asin"] != "") & (out["asin"].str.lower() != "nan")]
    return out.reset_index(drop=True)


def apply_current_inventory_snapshot(inventory_history: pd.DataFrame, current_snapshot: pd.DataFrame) -> pd.DataFrame:
    """Replace/append latest current inventory point, preserving historical BigQuery rows."""
    if current_snapshot.empty:
        return inventory_history.copy()

    current = current_snapshot.copy()
    current["date"] = pd.to_datetime(current["date"]).dt.date
    for col in ["available", "fba_inventory", "inbound_shipped", "total_inventory"]:
        if col not in current.columns:
            current[col] = 0
        current[col] = pd.to_numeric(current[col], errors="coerce").fillna(0)
    current = current[["date", "asin", "available", "fba_inventory", "inbound_shipped", "total_inventory"]]
    current_date = current["date"].max()

    history = inventory_history.copy()
    if not history.empty:
        history["date"] = pd.to_datetime(history["date"]).dt.date
        history = history[history["date"] < current_date]
    combined = pd.concat([history, current], ignore_index=True)
    return combined.sort_values(["asin", "date"]).reset_index(drop=True)


def normalize_event_calendar(calendar: pd.DataFrame) -> pd.DataFrame:
    """Keep operational event calendar fields and parse inclusive date ranges."""
    cols = {str(c).strip().lower(): c for c in calendar.columns}
    required = ["event_code", "start_date", "end_date"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise ValueError(f"event_calendar missing columns: {missing}")

    out = calendar[[cols["event_code"], cols["start_date"], cols["end_date"]]].copy()
    out.columns = required
    out["event_code"] = out["event_code"].astype(str).str.strip().str.upper()
    out["start_date"] = pd.to_datetime(out["start_date"], errors="coerce").dt.date
    out["end_date"] = pd.to_datetime(out["end_date"], errors="coerce").dt.date
    out = out[(out["event_code"] != "") & out["start_date"].notna() & out["end_date"].notna()]
    out = out[out["end_date"] >= out["start_date"]]
    return out.drop_duplicates().reset_index(drop=True)


def expand_event_dates(calendar: pd.DataFrame) -> list[date]:
    dates: set[date] = set()
    if calendar.empty:
        return []
    for row in calendar.itertuples(index=False):
        cursor = row.start_date
        while cursor <= row.end_date:
            dates.add(cursor)
            cursor += timedelta(days=1)
    return sorted(dates)


def events_for_projection_date(calendar: pd.DataFrame, day: date) -> pd.DataFrame:
    if calendar.empty:
        return pd.DataFrame(columns=["event_code", "start_date", "end_date"])
    return calendar[(calendar["start_date"] <= day) & (calendar["end_date"] >= day)].copy()


def calculate_event_forecast_total(
    asin: str,
    avg_units: float,
    event_code: str,
    event_duration: int,
    event_performance: pd.DataFrame,
) -> float | None:
    """Return total event-unit forecast for one ASIN/event using restock_2025 formula."""
    if event_duration <= 0 or event_performance.empty:
        return None

    df = event_performance.copy()
    asin_col = "ASIN" if "ASIN" in df.columns else "asin" if "asin" in df.columns else None
    avg_col = f"Average {event_code} sales, units (total)"
    best_col = f"Best {event_code} performance"
    if asin_col is None or avg_col not in df.columns or best_col not in df.columns:
        return None

    match = df[df[asin_col].astype(str).str.strip() == str(asin).strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    average_event = float(pd.to_numeric(pd.Series([row.get(avg_col)]), errors="coerce").fillna(0).iloc[0])
    best_perf = float(pd.to_numeric(pd.Series([row.get(best_col)]), errors="coerce").fillna(0).iloc[0])

    strong_performance = avg_units * best_perf
    poor_performance = avg_units * event_duration * 2
    forecast_total = (average_event + poor_performance) / 2
    if avg_units >= 3:
        forecast_total = ((average_event + strong_performance) / 2) * 1.2
    return max(float(forecast_total), 0.0)


def daily_projection_demands(
    asin: str,
    avg_units: float,
    start_date: date,
    projection_days: int,
    event_calendar: pd.DataFrame | None = None,
    event_performance: pd.DataFrame | None = None,
) -> list[tuple[date, float, str]]:
    """Build day-by-day demand schedule; event days replace baseline demand."""
    calendar = event_calendar if event_calendar is not None else pd.DataFrame()
    performance = event_performance if event_performance is not None else pd.DataFrame()
    demands: list[tuple[date, float, str]] = []
    for offset in range(1, projection_days + 1):
        day = start_date + timedelta(days=offset)
        demand = max(float(avg_units or 0), 0.0)
        event_code = ""
        overlapping = events_for_projection_date(calendar, day)
        if not overlapping.empty:
            candidates: list[tuple[float, str]] = []
            for event in overlapping.itertuples(index=False):
                duration = (event.end_date - event.start_date).days + 1
                forecast_total = calculate_event_forecast_total(
                    asin=asin,
                    avg_units=demand,
                    event_code=event.event_code,
                    event_duration=duration,
                    event_performance=performance,
                )
                if forecast_total is not None:
                    candidates.append((forecast_total / duration, event.event_code))
            if candidates:
                demand, event_code = max(candidates, key=lambda item: item[0])
        demands.append((day, demand, event_code))
    return demands


def project_inventory(
    asin: str,
    current_total: float,
    avg_units: float,
    start_date: date,
    projection_days: int,
    event_calendar: pd.DataFrame | None = None,
    event_performance: pd.DataFrame | None = None,
) -> tuple[list[dict], float, object, float]:
    """Project Total FBA depletion with optional event-day demand replacement."""
    remaining = max(float(current_total or 0), 0.0)
    projected_rows = [{"date": start_date, "projected_inventory": remaining}]
    stockout_days = np.inf
    stockout_date: object = pd.NaT
    consumed = 0.0

    for index, (day, demand, _event_code) in enumerate(
        daily_projection_demands(asin, avg_units, start_date, projection_days, event_calendar, event_performance),
        start=1,
    ):
        if demand > 0 and np.isinf(stockout_days) and remaining <= demand:
            stockout_days = (index - 1) + (remaining / demand)
            stockout_date = start_date + timedelta(days=int(np.floor(stockout_days)))
        consumed += demand
        remaining = max(float(current_total or 0) - consumed, 0.0)
        projected_rows.append({"date": day, "projected_inventory": remaining})

    projected_remaining = projected_rows[-1]["projected_inventory"] if projected_rows else max(float(current_total or 0), 0.0)
    if np.isinf(stockout_days) and avg_units > 0:
        stockout_days = projection_days + (projected_remaining / float(avg_units))
        stockout_date = start_date + timedelta(days=int(np.floor(stockout_days)))
    return projected_rows, stockout_days, stockout_date, projected_remaining


def build_restock_summary(
    sales: pd.DataFrame,
    inventory_history: pd.DataFrame,
    dictionary: pd.DataFrame,
    config: RestockConfig = RestockConfig(),
    event_dates: Iterable[date] | None = None,
    event_calendar: pd.DataFrame | None = None,
    event_performance: pd.DataFrame | None = None,
    selected_asins: Collection[str] | None = None,
) -> pd.DataFrame:
    selected_asin_set = (
        {str(asin).strip() for asin in selected_asins if str(asin).strip()}
        if selected_asins is not None
        else None
    )
    if selected_asin_set is not None and not selected_asin_set:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    if selected_asin_set is not None:
        if "asin" in sales.columns:
            sales = sales[sales["asin"].astype(str).isin(selected_asin_set)].copy()
        if "asin" in inventory_history.columns:
            inventory_history = inventory_history[inventory_history["asin"].astype(str).isin(selected_asin_set)].copy()
        if "asin" in dictionary.columns:
            dictionary = dictionary[dictionary["asin"].astype(str).isin(selected_asin_set)].copy()

    if inventory_history.empty and sales.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    inv_for_isr = inventory_history.rename(columns={"fba_inventory": "amz_inventory"})
    isr = calculate_inventory_isr(inv_for_isr, col_to_use="asin") if not inv_for_isr.empty else pd.DataFrame(columns=["asin", "ISR", "ISR_short"])
    smart_sales = calculate_smart_asin_sales(
        sales,
        isr,
        include_events=config.include_events,
        long_term_days=config.long_term_days,
        short_term_days=config.short_term_days,
        events=event_dates,
    )

    latest_date = inventory_history["date"].max() if not inventory_history.empty else date.today()
    current_inventory = inventory_history[inventory_history["date"] == latest_date].copy()

    dict_norm = normalize_dictionary(dictionary)
    meta = (
        dict_norm.groupby("asin", as_index=False)
        .agg(
            collection=("collection", lambda s: _join_unique(s, limit=3)),
            sub_collection=("sub_collection", lambda s: _join_unique(s, limit=3)),
            short_title=("short_title", lambda s: _first_non_empty(s)),
            sku_count=("sku", "nunique"),
            skus=("sku", lambda s: _join_unique(s, limit=8)),
        )
        if not dict_norm.empty
        else pd.DataFrame(columns=["asin", "collection", "sub_collection", "short_title", "sku_count", "skus"])
    )

    summary = pd.merge(smart_sales, current_inventory, on="asin", how="left", validate="1:1")
    summary = pd.merge(summary, meta, on="asin", how="left", validate="1:1")

    rename_map = {
        "avg units": "avg_units",
        "avg $": "avg_dollars",
        f"avg sales units, {config.short_term_days} days": "avg_units_short",
        f"avg sales units, {config.long_term_days} days": "avg_units_long",
        f"avg sales dollar, {config.short_term_days} days": "avg_dollars_short",
        f"avg sales dollar, {config.long_term_days} days": "avg_dollars_long",
        "ISR": "isr",
        "ISR_short": "isr_short",
    }
    summary = summary.rename(columns=rename_map)

    for col in ["available", "fba_inventory", "inbound_shipped", "total_inventory", "avg_units", "avg_dollars"]:
        summary[col] = pd.to_numeric(summary.get(col, 0), errors="coerce").fillna(0)

    # Projection/stockout use Total FBA. For SP-API current snapshots this is
    # `afn-total-quantity`; BigQuery fallback keeps its Inventory_Supply_at_FBA meaning.
    today = latest_date if isinstance(latest_date, date) else date.today()
    if event_calendar is not None and not event_calendar.empty and event_performance is not None and not event_performance.empty:
        projection_results = summary.apply(
            lambda row: project_inventory(
                asin=str(row["asin"]),
                current_total=float(row.get("fba_inventory", 0) or 0),
                avg_units=float(row.get("avg_units", 0) or 0),
                start_date=today,
                projection_days=config.projection_days,
                event_calendar=event_calendar,
                event_performance=event_performance,
            ),
            axis=1,
        )
        summary["days_to_stockout"] = [result[1] for result in projection_results]
        summary["stockout_date"] = [result[2] for result in projection_results]
        summary["projected_inventory_30d"] = [result[3] for result in projection_results]
    else:
        summary["days_to_stockout"] = np.where(
            summary["avg_units"] > 0,
            summary["fba_inventory"] / summary["avg_units"],
            np.inf,
        )
        summary["stockout_date"] = summary["days_to_stockout"].apply(
            lambda days: today + timedelta(days=int(np.floor(days))) if np.isfinite(days) else pd.NaT
        )
        summary["projected_inventory_30d"] = (
            summary["fba_inventory"] - (summary["avg_units"] * config.projection_days)
        ).clip(lower=0)
    summary["alert"] = summary["days_to_stockout"] < config.alert_days

    for col in SUMMARY_COLUMNS:
        if col not in summary.columns:
            summary[col] = "" if col in {"collection", "sub_collection", "short_title", "skus"} else 0

    return (
        summary[SUMMARY_COLUMNS]
        .sort_values("avg_dollars", ascending=False)
        .head(config.top_n)
        .reset_index(drop=True)
    )


def build_chart_series(
    asin: str,
    inventory_history: pd.DataFrame,
    summary_row: pd.Series,
    history_days: int = DEFAULT_HISTORY_DAYS,
    projection_days: int = DEFAULT_PROJECTION_DAYS,
    event_calendar: pd.DataFrame | None = None,
    event_performance: pd.DataFrame | None = None,
) -> pd.DataFrame:
    actual = inventory_history[inventory_history["asin"] == asin].copy()
    if not actual.empty:
        max_date = actual["date"].max()
        actual = actual[actual["date"] >= max_date - timedelta(days=history_days - 1)]
        actual = actual.sort_values("date")
    else:
        max_date = date.today()
        actual = pd.DataFrame(columns=["date", "total_inventory"])

    current_total = float(summary_row.get("fba_inventory", 0) or 0)
    avg_units = float(summary_row.get("avg_units", 0) or 0)
    future_rows, _days_to_stockout, _stockout_date, _projected_remaining = project_inventory(
        asin=asin,
        current_total=current_total,
        avg_units=avg_units,
        start_date=max_date,
        projection_days=projection_days,
        event_calendar=event_calendar,
        event_performance=event_performance,
    )
    future = pd.DataFrame(future_rows)

    actual_cols = ["date", "available", "fba_inventory", "total_inventory"]
    for col in actual_cols:
        if col not in actual.columns:
            actual[col] = np.nan
    actual_out = actual[actual_cols].rename(
        columns={
            "available": "available_inventory",
            "fba_inventory": "total_fba_inventory",
            "total_inventory": "fba_plus_shipped_inventory",
        }
    )
    combined = pd.merge(actual_out, future, on="date", how="outer").sort_values("date")
    return combined


def make_inventory_chart_options(series: pd.DataFrame, asin: str, alert: bool = False) -> dict:
    dates = pd.to_datetime(series["date"]).dt.strftime("%m/%d").tolist()
    available = [int(round(x)) if pd.notna(x) else None for x in series.get("available_inventory", pd.Series(dtype=float)).tolist()]
    total_fba = [int(round(x)) if pd.notna(x) else None for x in series.get("total_fba_inventory", pd.Series(dtype=float)).tolist()]
    projected = [round(float(x), 1) if pd.notna(x) else None for x in series.get("projected_inventory", pd.Series(dtype=float)).tolist()]
    projection_color = "#d71920" if alert else "#2f80ed"
    bg = "#fff1f1" if alert else "#ffffff"
    return {
        "backgroundColor": bg,
        "tooltip": {"trigger": "axis", "confine": True},
        "legend": {"show": True, "top": 0, "textStyle": {"fontSize": 9}, "itemWidth": 12, "itemHeight": 8},
        "grid": {"left": 38, "right": 12, "top": 34, "bottom": 28},
        "xAxis": {"type": "category", "data": dates, "axisLabel": {"fontSize": 9, "hideOverlap": True}},
        "yAxis": {"type": "value", "min": 0, "axisLabel": {"fontSize": 9}},
        "series": [
            {
                "name": "Available",
                "type": "line",
                "data": available,
                "connectNulls": False,
                "showSymbol": False,
                "lineStyle": {"width": 2, "color": "#27ae60"},
                "itemStyle": {"color": "#27ae60"},
            },
            {
                "name": "Total FBA",
                "type": "line",
                "data": total_fba,
                "connectNulls": False,
                "showSymbol": False,
                "lineStyle": {"width": 2, "color": "#4f4f4f"},
                "itemStyle": {"color": "#4f4f4f"},
            },
            {
                "name": "Projected Total FBA",
                "type": "line",
                "data": projected,
                "connectNulls": False,
                "showSymbol": False,
                "lineStyle": {"width": 3, "type": "dashed", "color": projection_color},
                "itemStyle": {"color": projection_color},
                "markLine": {"silent": True, "data": [{"yAxis": 0}]},
            },
        ],
    }


def apply_summary_filters(
    summary: pd.DataFrame,
    filtered_dictionary: pd.DataFrame | None = None,
    red_alerts_only: bool = False,
    search: str = "",
) -> pd.DataFrame:
    """Apply Restock visible-row filters in the same order the page displays them."""
    visible = summary.copy()
    if filtered_dictionary is not None and not filtered_dictionary.empty and "asin" in filtered_dictionary.columns:
        selected_asins = {
            str(asin).strip()
            for asin in filtered_dictionary["asin"].dropna().astype(str).tolist()
            if str(asin).strip()
        }
        if selected_asins:
            visible = visible[visible["asin"].astype(str).isin(selected_asins)]

    query = str(search or "").strip().lower()
    if query:
        mask = (
            visible["asin"].astype(str).str.lower().str.contains(query, na=False)
            | visible["short_title"].astype(str).str.lower().str.contains(query, na=False)
            | visible["collection"].astype(str).str.lower().str.contains(query, na=False)
            | visible["skus"].astype(str).str.lower().str.contains(query, na=False)
        )
        visible = visible[mask]

    if red_alerts_only:
        visible = visible[visible["alert"].astype(bool)]

    return visible.reset_index(drop=True)


def build_sales_query(days_to_pull: int) -> str:
    return f"""
        SELECT
            CAST(DATETIME(purchase_date, "America/Los_Angeles") AS DATE) AS date,
            sku,
            asin,
            SUM(quantity) AS unit_sales,
            SUM(item_price) AS dollar_sales
        FROM `mellanni-project-da.reports.all_orders`
        WHERE CAST(DATETIME(purchase_date, "America/Los_Angeles") AS DATE)
              BETWEEN DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL {int(days_to_pull)} DAY)
                  AND CURRENT_DATE("America/Los_Angeles")
          AND sales_channel = 'Amazon.com'
        GROUP BY date, sku, asin
        ORDER BY date, sku, asin
    """


def build_inventory_query(days_to_pull: int) -> str:
    return f"""
        SELECT
            DATE(snapshot_date) AS date,
            sku,
            asin,
            available,
            Inventory_Supply_at_FBA AS fba_inventory,
            inbound_shipped
        FROM `mellanni-project-da.reports.fba_inventory_planning`
        WHERE marketplace = 'US'
          AND DATE(snapshot_date) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {int(days_to_pull)} DAY)
                                      AND CURRENT_DATE()
        ORDER BY date DESC, sku ASC
    """


def query_dataframe(client: bigquery.Client, query: str) -> pd.DataFrame:
    return client.query(query).to_dataframe()


def _join_unique(values: pd.Series, limit: int = 5) -> str:
    items = [str(v).strip() for v in values.dropna().unique().tolist() if str(v).strip()]
    shown = items[:limit]
    suffix = f" +{len(items) - limit}" if len(items) > limit else ""
    return ", ".join(shown) + suffix


def _first_non_empty(values: pd.Series) -> str:
    for value in values.dropna().astype(str):
        if value.strip():
            return value.strip()
    return ""
