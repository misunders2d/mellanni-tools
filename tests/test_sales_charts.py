import pandas as pd

from modules import sales_charts


def _sales_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-06-01").date(), pd.Timestamp("2026-06-02").date()],
            "units": [10, 20],
            "forecast_units": [11, 21],
            "sessions": [100, 200],
            "30-day avg": [9, 19],
            "available": [50, 60],
            "inventory_supply_at_fba": [55, 65],
            "stockout": [0, 0],
            "change_notes": ["Price change: test note", ""],
        }
    )


def _ads_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-06-01").date(), pd.Timestamp("2026-06-02").date()],
            "ad_spend": [1.25, 2.50],
            "total_sales": [10.0, 20.0],
            "total_units": [1, 2],
            "clicks": [5, 10],
            "impressions": [100, 200],
        }
    )


def test_change_note_markpoint_uses_date_category(monkeypatch):
    captured = {}

    def fake_st_echarts(options, **kwargs):
        captured["options"] = options
        captured["kwargs"] = kwargs

    monkeypatch.setattr(sales_charts, "st_echarts", fake_st_echarts)

    sales_charts.render_sales_chart(_sales_df(), _ads_df(), show_change_notes=True)

    units_series = captured["options"]["series"][0]
    mark_points = units_series["markPoint"]["data"]

    assert mark_points[0]["coord"] == ["2026-06-01", 10]
    assert mark_points[0]["coord"][0] in captured["options"]["xAxis"][0]["data"]
    assert mark_points[0]["coord"][0] != 0
