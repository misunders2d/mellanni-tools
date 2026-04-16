"""SQP Analytics — ECharts visualizations for Search Query Performance data.

Each function returns an ECharts options dict ready for st_echarts().
All JsCode formatters must be single-line (streamlit_echarts frontend limitation).
"""

import json
from datetime import datetime

import pandas as pd
from streamlit_echarts import JsCode


# ---------------------------------------------------------------------------
# Help texts — displayed alongside each chart
# ---------------------------------------------------------------------------

HELP = {
    "funnel": (
        "**How to read:** The left funnel shows the total market, the right shows your ASIN. "
        "Compare the width at each stage. If your funnel narrows faster than the market, "
        "you're losing customers at that stage.\n\n"
        "**Action:** If your click share is much lower than impression share, your listing "
        "image/title needs work. If cart-add share drops vs click share, your price or "
        "detail page is the problem. If purchase share drops vs cart-add, check pricing, "
        "shipping speed, or stock issues."
    ),
    "sankey": (
        "**How to read:** Your ASIN's journey from search to purchase. At each stage, "
        "the green flow continues to the next step; the red flow is dropped customers. "
        "Hover any link to see the exact count.\n\n"
        "**Action:** Find the widest red flow — that's your biggest leak. "
        "Search → Impression loss = visibility problem (PPC, SEO, ranking). "
        "Impression → Click loss = listing image/title. "
        "Click → Cart loss = detail page content or price. "
        "Cart → Purchase loss = checkout friction (shipping, stock, buy box)."
    ),
    "strategy_matrix": (
        "**How to read:** Each bubble is a keyword. X = search volume (market size), "
        "Y = your impression share (visibility), bubble size = your purchase count (revenue).\n\n"
        "**Quadrants:**\n"
        "- **Top-right (Stars):** High volume + high share — protect these, don't cut ad spend\n"
        "- **Bottom-right (Opportunities):** High volume + low share — biggest growth potential, invest in PPC and listing optimization\n"
        "- **Top-left (Niche wins):** Low volume + high share — efficient but small, maintain\n"
        "- **Bottom-left (Ignore):** Low volume + low share — don't waste resources here"
    ),
    "leakage_heatmap": (
        "**How to read:** Each row is a keyword, each column is a funnel stage. "
        "Darker red = higher drop-off rate at that stage. Look for patterns.\n\n"
        "**Action:** If a column is consistently red across keywords, it's a systemic issue "
        "(e.g., all keywords drop at cart-add = price problem). If a specific row is red "
        "at one stage, it's a keyword-specific issue (e.g., wrong search intent, listing "
        "doesn't match what the customer expected)."
    ),
    "missed_opportunity": (
        "**How to read:** Each bar shows estimated lost revenue from keywords where your "
        "ASIN didn't appear for some searches. Sorted by dollar value.\n\n"
        "**Action:** Focus PPC spend on the top keywords in this chart. These are searches "
        "where customers are buying products like yours, but they never see your listing."
    ),
    "price_position": (
        "**How to read:** X = how much more expensive you are vs the market median "
        "(negative = you're cheaper). Y = your purchase share for that keyword. "
        "Bubble size = search volume.\n\n"
        "**Action:** Keywords in the top-left (cheaper + high share) are your sweet spot. "
        "Keywords in the bottom-right (more expensive + low share) suggest price is hurting you. "
        "Keywords where you're expensive but still have high share indicate strong brand/listing."
    ),
    "share_of_voice": (
        "**How to read:** Each line tracks your share at a funnel stage over time. "
        "Ideally all lines trend up. If impression share grows but purchase share doesn't, "
        "you're getting visibility but not converting.\n\n"
        "**Action:** Diverging lines (e.g., impression share up, purchase share flat) "
        "signal a conversion problem that appeared at a specific point in time — "
        "check what changed (price, reviews, stock, competitor launch)."
    ),
    "keyword_momentum": (
        "**How to read:** Each block is a keyword, sized by search volume. "
        "Color indicates momentum: green = gaining share, red = losing share, "
        "gray = stable.\n\n"
        "**Action:** Red blocks need immediate attention — you're losing ground. "
        "Check if a competitor launched, if your ranking dropped, or if your ad bids "
        "are being outcompeted. Green blocks are working — learn what's different about them."
    ),
    "parallel_coordinates": (
        "**How to read:** Each vertical axis is a metric. Each line is a keyword, "
        "connecting its values across all metrics. Lines that stay high across all axes "
        "are strong performers. Lines that drop sharply at a specific axis reveal "
        "where that keyword underperforms.\n\n"
        "**Action:** Drag along any axis to filter — this highlights only the keywords "
        "within that range. Use this to find keywords with high search volume but low "
        "ASIN conversion (drag the volume axis high, look for lines that drop at conversion). "
        "Color indicates search volume tier: blue = high volume, red = low volume."
    ),
    "cart_abandonment": (
        "**How to read:** For each keyword, two bars — your ASIN's cart-abandonment rate "
        "(color-coded: green = low, red = high) and the niche's rate for that same keyword "
        "(gray). The dashed line shows the niche average across the shown keywords.\n\n"
        "**Action:** When your bar is noticeably longer than the niche bar for the same keyword, "
        "you're losing more customers at checkout than competitors on that query — investigate "
        "price shock, shipping cost, delivery time, stock issues, or Buy Box loss."
    ),
}


# ---------------------------------------------------------------------------
# 1. Conversion Funnel
# ---------------------------------------------------------------------------

def funnel_chart(combined_report: pd.DataFrame) -> dict | None:
    if combined_report.empty:
        return None

    row = combined_report.iloc[0]

    market_data = [
        {"value": float(row.get("totalQueryImpressionCount", 0)), "name": "Impressions"},
        {"value": float(row.get("totalClickCount", 0)), "name": "Clicks"},
        {"value": float(row.get("totalCartAddCount", 0)), "name": "Cart Adds"},
        {"value": float(row.get("totalPurchaseCount", 0)), "name": "Purchases"},
    ]

    asin_data = [
        {"value": float(row.get("asinImpressionCount", 0)), "name": "Impressions"},
        {"value": float(row.get("asinClickCount", 0)), "name": "Clicks"},
        {"value": float(row.get("asinCartAddCount", 0)), "name": "Cart Adds"},
        {"value": float(row.get("asinPurchaseCount", 0)), "name": "Purchases"},
    ]

    # Attach percentage relative to the top of each funnel
    def _attach_pct(data: list) -> list:
        top = data[0]["value"] or 1
        for d in data:
            d["pct"] = round(d["value"] / top * 100, 3)
        return data

    market_data = _attach_pct(market_data)
    asin_data = _attach_pct(asin_data)

    label_formatter = JsCode("function(p) { return p.name + '\\n' + p.value.toLocaleString() + ' (' + p.data.pct + '%)'; }").js_code
    tooltip_formatter = JsCode("function(p) { return p.seriesName + '<br/>' + p.name + ': <b>' + p.value.toLocaleString() + '</b> (' + p.data.pct + '%)'; }").js_code

    return {
        "title": [
            {"text": "Market Funnel", "left": "25%", "textAlign": "center", "textStyle": {"fontSize": 14}},
            {"text": "Your ASIN Funnel", "left": "75%", "textAlign": "center", "textStyle": {"fontSize": 14}},
        ],
        "tooltip": {"trigger": "item", "formatter": tooltip_formatter},
        "legend": {"show": False},
        "series": [
            {
                "name": "Market",
                "type": "funnel",
                "left": "5%",
                "width": "40%",
                "sort": "descending",
                "gap": 2,
                "label": {"show": True, "position": "inside", "formatter": label_formatter},
                "itemStyle": {"borderWidth": 1, "borderColor": "#fff"},
                "data": market_data,
            },
            {
                "name": "Your ASIN",
                "type": "funnel",
                "left": "55%",
                "width": "40%",
                "sort": "descending",
                "gap": 2,
                "label": {"show": True, "position": "inside", "formatter": label_formatter},
                "itemStyle": {"borderWidth": 1, "borderColor": "#fff"},
                "data": asin_data,
            },
        ],
        "color": ["#89b4fa", "#74c7ec", "#94e2d5", "#a6e3a1", "#f9e2af"],
    }


def asin_sankey_chart(
    combined_report: pd.DataFrame,
    show_dropoffs: bool = True,
) -> dict | None:
    """Sankey flow showing ASIN journey from search to purchase.

    When show_dropoffs=False, only the "continuing" flows are shown (no red loss branches).
    """
    if combined_report.empty:
        return None

    row = combined_report.iloc[0]
    search_vol = float(row.get("searchQueryVolume", 0))
    impressions = float(row.get("asinImpressionCount", 0))
    clicks = float(row.get("asinClickCount", 0))
    cart_adds = float(row.get("asinCartAddCount", 0))
    purchases = float(row.get("asinPurchaseCount", 0))

    def _pct(value: float, parent: float) -> float:
        return round(value / parent * 100, 3) if parent else 0

    # Each node's % is its share of the parent stage
    def _label(name: str, value: float, parent: float | None) -> str:
        if parent is None:
            return f"{name}\n{int(value):,} (100%)"
        return f"{name}\n{int(value):,} ({_pct(value, parent)}%)"

    stage_nodes = [
        {"name": _label("Search Volume", search_vol, None), "itemStyle": {"color": "#89b4fa"}},
        {"name": _label("Impressions", impressions, search_vol), "itemStyle": {"color": "#74c7ec"}},
        {"name": _label("Clicks", clicks, impressions), "itemStyle": {"color": "#94e2d5"}},
        {"name": _label("Cart Adds", cart_adds, clicks), "itemStyle": {"color": "#a6e3a1"}},
        {"name": _label("Purchases", purchases, cart_adds), "itemStyle": {"color": "#f9e2af"}},
    ]

    green = {"color": "#a6e3a1", "opacity": 0.5}
    red = {"color": "#f38ba8", "opacity": 0.4}

    # Resolve node names by index so we don't repeat long strings
    sv, imp, clk, atc, pur = [n["name"] for n in stage_nodes]

    links = [
        {"source": sv, "target": imp, "value": impressions, "lineStyle": green},
        {"source": imp, "target": clk, "value": clicks, "lineStyle": green},
        {"source": clk, "target": atc, "value": cart_adds, "lineStyle": green},
        {"source": atc, "target": pur, "value": purchases, "lineStyle": green},
    ]

    nodes = list(stage_nodes)

    if show_dropoffs:
        lost_impression = max(0, search_vol - impressions)
        lost_click = max(0, impressions - clicks)
        lost_cart = max(0, clicks - cart_adds)
        lost_purchase = max(0, cart_adds - purchases)

        drop_nodes = [
            {"name": _label("Lost (no impression)", lost_impression, search_vol), "itemStyle": {"color": "#f38ba8"}},
            {"name": _label("Lost (no click)", lost_click, impressions), "itemStyle": {"color": "#f38ba8"}},
            {"name": _label("Lost (no cart)", lost_cart, clicks), "itemStyle": {"color": "#f38ba8"}},
            {"name": _label("Lost (no purchase)", lost_purchase, cart_adds), "itemStyle": {"color": "#f38ba8"}},
        ]
        nodes.extend(drop_nodes)
        l_imp, l_clk, l_atc, l_pur = [n["name"] for n in drop_nodes]

        links.extend([
            {"source": sv, "target": l_imp, "value": lost_impression, "lineStyle": red},
            {"source": imp, "target": l_clk, "value": lost_click, "lineStyle": red},
            {"source": clk, "target": l_atc, "value": lost_cart, "lineStyle": red},
            {"source": atc, "target": l_pur, "value": lost_purchase, "lineStyle": red},
        ])

    tooltip_formatter = JsCode("function(p) { if (p.dataType === 'edge') { return p.data.source.split('\\n')[0] + ' → ' + p.data.target.split('\\n')[0] + '<br/><b>' + p.value.toLocaleString() + '</b>'; } return '<b>' + p.name + '</b>'; }").js_code

    return {
        "tooltip": {"trigger": "item", "formatter": tooltip_formatter},
        "toolbox": {
            "feature": {
                "saveAsImage": {"title": "Save as image"},
            },
            "right": "2%",
            "top": "2%",
        },
        "series": [{
            "type": "sankey",
            "data": nodes,
            "links": links,
            "emphasis": {"focus": "adjacency"},
            "nodeAlign": "left",
            "nodeGap": 16,
            "label": {"fontSize": 12, "fontWeight": "bold"},
            "left": "3%",
            "right": "15%",
            "top": "3%",
            "bottom": "3%",
        }],
    }


# ---------------------------------------------------------------------------
# 2. Keyword Strategy Matrix (bubble scatter)
# ---------------------------------------------------------------------------

def strategy_matrix(query_report: pd.DataFrame, top_n: int | None = None) -> dict | None:
    if query_report.empty:
        return None

    # Bubble charts scale fine to 100+ points — use all keywords unless capped explicitly
    df = query_report.nlargest(top_n, "searchQueryVolume").copy() if top_n else query_report.copy()

    # Ensure numeric
    for col in ["searchQueryVolume", "asinImpressionShare", "asinPurchaseCount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    max_purchases = df["asinPurchaseCount"].max() or 1
    vol_min = max(1, float(df["searchQueryVolume"].min()) * 0.9)
    vol_max = float(df["searchQueryVolume"].max()) * 1.1
    share_max = float(df["asinImpressionShare"].max()) * 100 * 1.15

    data = []
    for _, row in df.iterrows():
        data.append({
            "value": [
                float(row["searchQueryVolume"]),
                round(float(row["asinImpressionShare"]) * 100, 2),
                float(row["asinPurchaseCount"]),
            ],
            "name": str(row["searchQuery"]),
            "symbolSize": max(8, min(60, float(row["asinPurchaseCount"]) / max_purchases * 60)),
        })

    return {
        "tooltip": {"formatter": JsCode("function(p) { return '<b>' + p.name + '</b><br/>Search Volume: ' + p.value[0].toLocaleString() + '<br/>Impression Share: ' + p.value[1] + '%<br/>Purchases: ' + p.value[2].toLocaleString(); }").js_code},
        "xAxis": {
            "type": "log",
            "name": "Search Volume",
            "nameLocation": "center",
            "nameGap": 30,
            "min": vol_min,
            "max": vol_max,
            "splitLine": {"show": True, "lineStyle": {"type": "dashed", "opacity": 0.3}},
        },
        "yAxis": {
            "type": "value",
            "name": "Impression Share (%)",
            "nameLocation": "center",
            "nameGap": 40,
            "max": share_max,
            "splitLine": {"show": True, "lineStyle": {"type": "dashed", "opacity": 0.3}},
        },
        "series": [{"type": "scatter", "data": data}],
        "visualMap": {
            "show": False,
            "dimension": 1,
            "min": 0,
            "max": 100,
            "inRange": {"color": ["#f38ba8", "#f9e2af", "#a6e3a1"]},
        },
        "grid": {"left": "8%", "right": "5%", "bottom": "12%", "top": "5%"},
        # Quadrant lines
        "markLine": {"silent": True},
    }


# ---------------------------------------------------------------------------
# 3. Funnel Leakage Heatmap
# ---------------------------------------------------------------------------

def funnel_leakage_heatmap(query_report: pd.DataFrame, top_n: int = 20) -> dict | None:
    if query_report.empty:
        return None

    df = query_report.nlargest(top_n, "searchQueryVolume").copy()
    for col in ["asinImpressionCount", "asinClickCount", "asinCartAddCount", "asinPurchaseCount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    stages = ["Impression→Click", "Click→Cart", "Cart→Purchase"]
    keywords = df["searchQuery"].tolist()

    data = []
    for i, (_, row) in enumerate(df.iterrows()):
        imp = float(row.get("asinImpressionCount", 0))
        clk = float(row.get("asinClickCount", 0))
        atc = float(row.get("asinCartAddCount", 0))
        pur = float(row.get("asinPurchaseCount", 0))

        drop_imp_clk = round((1 - clk / imp) * 100, 1) if imp > 0 else 0
        drop_clk_atc = round((1 - atc / clk) * 100, 1) if clk > 0 else 0
        drop_atc_pur = round((1 - pur / atc) * 100, 1) if atc > 0 else 0

        data.append([0, i, drop_imp_clk])
        data.append([1, i, drop_clk_atc])
        data.append([2, i, drop_atc_pur])

    return {
        "tooltip": {"formatter": JsCode("function(p) { return '<b>' + p.name + '</b><br/>' + p.value[2] + '% drop-off'; }").js_code},
        "xAxis": {"type": "category", "data": stages, "splitArea": {"show": True}, "position": "top"},
        "yAxis": {"type": "category", "data": keywords, "inverse": True, "axisLabel": {"fontSize": 11}},
        "visualMap": {
            "min": 0,
            "max": 100,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "0%",
            "inRange": {"color": ["#a6e3a1", "#f9e2af", "#f38ba8"]},
            "text": ["High drop-off", "Low drop-off"],
        },
        "grid": {"left": "20%", "right": "5%", "top": "8%", "bottom": "12%"},
        "series": [{
            "name": "Drop-off %",
            "type": "heatmap",
            "data": data,
            "label": {"show": True, "formatter": JsCode("function(p) { return p.value[2] + '%'; }").js_code},
            "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}},
        }],
    }


# ---------------------------------------------------------------------------
# 4. Missed Opportunity Bar
# ---------------------------------------------------------------------------

def missed_opportunity_chart(query_report: pd.DataFrame, top_n: int = 15) -> dict | None:
    if query_report.empty or "asinLostSales" not in query_report.columns:
        return None

    df = query_report.copy()
    df["asinLostSales"] = pd.to_numeric(df["asinLostSales"], errors="coerce").fillna(0)
    df = df[df["asinLostSales"] > 0].nlargest(top_n, "asinLostSales")

    if df.empty:
        return None

    keywords = df["searchQuery"].tolist()
    values = [round(float(v), 2) for v in df["asinLostSales"]]

    return {
        "title": {"text": "Estimated lost revenue by keyword", "textStyle": {"fontSize": 13, "fontWeight": "normal"}},
        "tooltip": {"formatter": JsCode("function(p) { return '<b>' + p.name + '</b><br/>Est. lost revenue: <b>$' + p.value.toLocaleString() + '</b>'; }").js_code},
        "xAxis": {"type": "value", "name": "Est. Lost Revenue ($)", "axisLabel": {"formatter": JsCode("function(v) { return '$' + v.toLocaleString(); }").js_code}},
        "yAxis": {"type": "category", "data": keywords, "inverse": True, "axisLabel": {"fontSize": 11}},
        "grid": {"left": "22%", "right": "8%", "top": "8%", "bottom": "5%"},
        "series": [{
            "type": "bar",
            "data": values,
            "itemStyle": {"color": "#fab387", "borderRadius": [0, 4, 4, 0]},
            "label": {"show": True, "position": "right", "formatter": JsCode("function(p) { return '$' + p.value.toLocaleString(); }").js_code},
        }],
    }


# ---------------------------------------------------------------------------
# 5. Competitive Price Position
# ---------------------------------------------------------------------------

def price_position_chart(query_report: pd.DataFrame, top_n: int | None = None) -> dict | None:
    if query_report.empty:
        return None

    needed = ["asinMedianPurchasePrice_amount", "totalMedianPurchasePrice_amount",
              "asinPurchaseShare", "searchQueryVolume", "searchQuery"]
    if not all(c in query_report.columns for c in needed):
        return None

    # Bubble chart — show all keywords unless explicitly capped
    df = query_report.nlargest(top_n, "searchQueryVolume").copy() if top_n else query_report.copy()
    for col in needed[:-1]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["priceGap"] = df["asinMedianPurchasePrice_amount"] - df["totalMedianPurchasePrice_amount"]
    df = df[df["totalMedianPurchasePrice_amount"] > 0]

    if df.empty:
        return None

    max_vol = df["searchQueryVolume"].max() or 1
    data = []
    for _, row in df.iterrows():
        data.append({
            "value": [
                round(float(row["priceGap"]), 2),
                round(float(row["asinPurchaseShare"]) * 100, 2),
                float(row["searchQueryVolume"]),
            ],
            "name": str(row["searchQuery"]),
            "symbolSize": max(8, min(50, float(row["searchQueryVolume"]) / max_vol * 50)),
        })

    return {
        "tooltip": {"formatter": JsCode("function(p) { return '<b>' + p.name + '</b><br/>Price gap: <b>$' + p.value[0].toFixed(2) + '</b><br/>Purchase share: <b>' + p.value[1] + '%</b><br/>Search volume: ' + p.value[2].toLocaleString(); }").js_code},
        "xAxis": {
            "type": "value",
            "name": "Price vs Market ($)",
            "nameLocation": "center",
            "nameGap": 30,
            "splitLine": {"show": True, "lineStyle": {"type": "dashed", "opacity": 0.3}},
        },
        "yAxis": {
            "type": "value",
            "name": "Purchase Share (%)",
            "nameLocation": "center",
            "nameGap": 40,
            "splitLine": {"show": True, "lineStyle": {"type": "dashed", "opacity": 0.3}},
        },
        "series": [{"type": "scatter", "data": data}],
        "visualMap": {
            "show": False,
            "dimension": 0,
            "min": -20,
            "max": 20,
            "inRange": {"color": ["#a6e3a1", "#cdd6f4", "#f38ba8"]},
        },
        "grid": {"left": "10%", "right": "5%", "bottom": "12%", "top": "5%"},
    }


# ---------------------------------------------------------------------------
# 6. Share of Voice Over Time (multi-week)
# ---------------------------------------------------------------------------

def share_of_voice_chart(date_report: pd.DataFrame) -> dict | None:
    if date_report.empty or len(date_report) < 2:
        return None

    df = date_report.copy()
    df["startDate"] = pd.to_datetime(df["startDate"]).dt.strftime("%b %d")

    share_cols = {
        "asinImpressionShare": "Impression Share",
        "asinClickShare": "Click Share",
        "asinCartAddShare": "Cart Add Share",
        "asinPurchaseShare": "Purchase Share",
    }

    dates = df["startDate"].tolist()
    series = []
    colors = ["#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af"]

    for i, (col, label) in enumerate(share_cols.items()):
        if col not in df.columns:
            continue
        values = [round(float(v) * 100, 2) for v in pd.to_numeric(df[col], errors="coerce").fillna(0)]
        series.append({
            "name": label,
            "type": "line",
            "smooth": True,
            "data": values,
            "symbol": "circle",
            "symbolSize": 8,
            "lineStyle": {"width": 2.5},
            "itemStyle": {"color": colors[i % len(colors)]},
        })

    return {
        "tooltip": {"trigger": "axis", "formatter": JsCode("function(ps) { var s = '<b>' + ps[0].name + '</b>'; for (var i=0; i<ps.length; i++) { s += '<br/>' + ps[i].marker + ' ' + ps[i].seriesName + ': <b>' + ps[i].value + '%</b>'; } return s; }").js_code},
        "legend": {"data": list(share_cols.values()), "top": "0%"},
        "xAxis": {"type": "category", "data": dates},
        "yAxis": {"type": "value", "name": "Share (%)", "axisLabel": {"formatter": "{value}%"}},
        "grid": {"left": "8%", "right": "5%", "bottom": "5%", "top": "15%"},
        "series": series,
    }


# ---------------------------------------------------------------------------
# 7. Keyword Momentum Treemap (multi-week)
# ---------------------------------------------------------------------------

def keyword_momentum_chart(date_query_report: pd.DataFrame, top_n: int = 30) -> dict | None:
    if date_query_report.empty:
        return None

    df = date_query_report.copy()
    df["startDate"] = pd.to_datetime(df["startDate"])

    dates = sorted(df["startDate"].unique())
    if len(dates) < 2:
        return None

    # Compare first vs last period
    first = df[df["startDate"] == dates[0]].set_index("searchQuery")
    last = df[df["startDate"] == dates[-1]].set_index("searchQuery")

    keywords = last.nlargest(top_n, "searchQueryVolume").index.tolist()

    tree_data = []
    for kw in keywords:
        if kw not in first.index or kw not in last.index:
            continue

        share_before = float(pd.to_numeric(first.loc[kw, "asinImpressionShare"], errors="coerce") or 0)
        share_after = float(pd.to_numeric(last.loc[kw, "asinImpressionShare"], errors="coerce") or 0)
        vol = float(pd.to_numeric(last.loc[kw, "searchQueryVolume"], errors="coerce") or 0)

        if share_before > 0:
            change = (share_after - share_before) / share_before * 100
        elif share_after > 0:
            change = 100
        else:
            change = 0

        tree_data.append({
            "name": str(kw),
            "value": [vol, round(change, 1)],
        })

    if not tree_data:
        return None

    return {
        "tooltip": {"formatter": JsCode("function(p) { var c = p.value[1]; var dir = c > 0 ? '+' : ''; return '<b>' + p.name + '</b><br/>Volume: ' + p.value[0].toLocaleString() + '<br/>Share change: <b>' + dir + c + '%</b>'; }").js_code},
        "series": [{
            "type": "treemap",
            "data": tree_data,
            "width": "95%",
            "height": "90%",
            "roam": False,
            "nodeClick": False,
            "breadcrumb": {"show": False},
            "label": {"show": True, "formatter": JsCode("function(p) { var c = p.value[1]; var dir = c > 0 ? '+' : ''; return p.name + '\\n' + dir + c + '%'; }").js_code, "fontSize": 11},
            "levels": [{"colorMappingBy": "value", "itemStyle": {"borderWidth": 2, "borderColor": "#1e1e2e", "gapWidth": 2}}],
        }],
        "visualMap": {
            "show": True,
            "type": "continuous",
            "dimension": 1,
            "min": -50,
            "max": 50,
            "inRange": {"color": ["#f38ba8", "#585b70", "#a6e3a1"]},
            "text": ["Gaining", "Losing"],
            "orient": "horizontal",
            "left": "center",
            "bottom": "0%",
        },
    }


# ---------------------------------------------------------------------------
# 8. Cart Abandonment
# ---------------------------------------------------------------------------

def cart_abandonment_chart(query_report: pd.DataFrame, top_n: int = 15) -> dict | None:
    if query_report.empty:
        return None

    numeric_cols = ["asinCartAddCount", "asinPurchaseCount", "totalCartAddCount",
                    "totalPurchaseCount", "searchQueryVolume"]
    needed = numeric_cols + ["searchQuery"]
    if not all(c in query_report.columns for c in needed):
        return None

    df = query_report.nlargest(top_n, "searchQueryVolume").copy()
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["asinAbandonment"] = df.apply(
        lambda r: round((1 - r["asinPurchaseCount"] / r["asinCartAddCount"]) * 100, 1)
        if r["asinCartAddCount"] > 0 else 0, axis=1
    )
    df["marketAbandonment"] = df.apply(
        lambda r: round((1 - r["totalPurchaseCount"] / r["totalCartAddCount"]) * 100, 1)
        if r["totalCartAddCount"] > 0 else 0, axis=1
    )

    market_avg = round(float(df["marketAbandonment"].mean()), 1)
    keywords = df["searchQuery"].tolist()
    asin_values = df["asinAbandonment"].tolist()
    market_values = df["marketAbandonment"].tolist()

    return {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "valueFormatter": JsCode("function(v) { return v + '%'; }").js_code},
        "legend": {"data": ["Your ASIN", "Niche"], "top": 0, "right": 10},
        "title": {"text": "Cart abandonment rate by keyword (top by volume)", "textStyle": {"fontSize": 13, "fontWeight": "normal"}},
        "xAxis": {"type": "value", "name": "Abandonment %", "axisLabel": {"formatter": "{value}%"}},
        "yAxis": {"type": "category", "data": keywords, "inverse": True, "axisLabel": {"fontSize": 11}},
        "grid": {"left": "22%", "right": "10%", "top": "12%", "bottom": "5%"},
        "series": [
            {
                "name": "Your ASIN",
                "type": "bar",
                "data": [float(a) for a in asin_values],
                "itemStyle": {"borderRadius": [0, 4, 4, 0]},
                "markLine": {
                    "silent": True,
                    "symbol": "none",
                    "lineStyle": {"type": "dashed", "color": "#cdd6f4", "width": 2},
                    "label": {"formatter": "Niche avg: {c}%", "position": "end"},
                    "data": [{"xAxis": market_avg}],
                },
            },
            {
                "name": "Niche",
                "type": "bar",
                "data": [float(m) for m in market_values],
                "itemStyle": {"color": "#94a3b8", "borderRadius": [0, 4, 4, 0], "opacity": 0.75},
            },
        ],
        "visualMap": {
            "show": False,
            "seriesIndex": 0,
            "dimension": 0,
            "min": 0,
            "max": 100,
            "inRange": {"color": ["#a6e3a1", "#f9e2af", "#f38ba8"]},
        },
    }


# ---------------------------------------------------------------------------
# Report builder — structured export for AI analysis
# ---------------------------------------------------------------------------

def _safe_num(val) -> float:
    try:
        n = float(val)
        return n if pd.notna(n) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _summarize_funnel(row: pd.Series, prefix: str) -> dict:
    """Build market or ASIN funnel summary with absolute + % values."""
    if prefix == "total":
        imp = _safe_num(row.get("totalQueryImpressionCount"))
    else:
        imp = _safe_num(row.get("asinImpressionCount"))
    clk = _safe_num(row.get(f"{prefix}ClickCount"))
    atc = _safe_num(row.get(f"{prefix}CartAddCount"))
    pur = _safe_num(row.get(f"{prefix}PurchaseCount"))

    return {
        "impressions": imp,
        "clicks": clk,
        "cart_adds": atc,
        "purchases": pur,
        "click_through_rate_pct": round(clk / imp * 100, 3) if imp else 0,
        "click_to_cart_rate_pct": round(atc / clk * 100, 3) if clk else 0,
        "cart_to_purchase_rate_pct": round(pur / atc * 100, 3) if atc else 0,
        "overall_conversion_pct": round(pur / imp * 100, 3) if imp else 0,
    }


def build_sqp_report(
    combined_report: pd.DataFrame,
    query_report: pd.DataFrame,
    date_report: pd.DataFrame,
    date_query_report: pd.DataFrame,
    asins: list[str] | None = None,
    filters: dict | None = None,
    top_n: int = 15,
) -> dict:
    """Build a structured JSON report for AI analysis.

    Returns a dict with:
    - metadata: date range, ASINs, filters
    - summary: funnel stats for market and ASIN
    - insights: pre-computed top opportunities, leakage stages, momentum changes
    - data: full tables for deep analysis
    """
    report: dict = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "report_type": "sqp_analysis",
        "metadata": {},
        "summary": {},
        "insights": {},
        "data": {},
    }

    # ---- metadata ----
    if not date_report.empty and "startDate" in date_report.columns:
        dates = pd.to_datetime(date_report["startDate"], errors="coerce").dropna()
        if not dates.empty:
            report["metadata"]["date_range"] = {
                "start": dates.min().strftime("%Y-%m-%d"),
                "end": dates.max().strftime("%Y-%m-%d"),
                "weeks_included": int(dates.nunique()),
            }
    report["metadata"]["asins_analyzed"] = asins or []
    report["metadata"]["filters"] = filters or {}
    report["metadata"]["keywords_total"] = len(query_report) if not query_report.empty else 0

    # ---- summary (funnels) ----
    if not combined_report.empty:
        row = combined_report.iloc[0]
        report["summary"]["market_funnel"] = _summarize_funnel(row, "total")
        report["summary"]["asin_funnel"] = _summarize_funnel(row, "asin")
        report["summary"]["search_volume_total"] = _safe_num(row.get("searchQueryVolume"))
        report["summary"]["asin_share"] = {
            "impression_share_pct": round(_safe_num(row.get("asinImpressionShare")) * 100, 3),
            "click_share_pct": round(_safe_num(row.get("asinClickShare")) * 100, 3),
            "cart_add_share_pct": round(_safe_num(row.get("asinCartAddShare")) * 100, 3),
            "purchase_share_pct": round(_safe_num(row.get("asinPurchaseShare")) * 100, 3),
        }

    # ---- insights ----

    # Top missed opportunities by lost sales
    if not query_report.empty and "asinLostSales" in query_report.columns:
        missed = query_report.copy()
        missed["asinLostSales"] = pd.to_numeric(missed["asinLostSales"], errors="coerce").fillna(0)
        missed = missed[missed["asinLostSales"] > 0].nlargest(top_n, "asinLostSales")
        report["insights"]["top_missed_opportunities"] = [
            {
                "keyword": str(r["searchQuery"]),
                "search_volume": int(_safe_num(r.get("searchQueryVolume"))),
                "impression_share_pct": round(_safe_num(r.get("asinImpressionShare")) * 100, 3),
                "estimated_lost_revenue_usd": round(float(r["asinLostSales"]), 2),
            }
            for _, r in missed.iterrows()
        ]

    # Worst funnel leakage points (per keyword)
    if not query_report.empty:
        leak_rows = []
        df = query_report.nlargest(top_n, "searchQueryVolume").copy()
        for _, r in df.iterrows():
            imp = _safe_num(r.get("asinImpressionCount"))
            clk = _safe_num(r.get("asinClickCount"))
            atc = _safe_num(r.get("asinCartAddCount"))
            pur = _safe_num(r.get("asinPurchaseCount"))
            leak_rows.append({
                "keyword": str(r["searchQuery"]),
                "search_volume": int(_safe_num(r.get("searchQueryVolume"))),
                "impression_to_click_dropoff_pct": round((1 - clk / imp) * 100, 1) if imp else None,
                "click_to_cart_dropoff_pct": round((1 - atc / clk) * 100, 1) if clk else None,
                "cart_to_purchase_dropoff_pct": round((1 - pur / atc) * 100, 1) if atc else None,
            })
        report["insights"]["funnel_leakage_by_keyword"] = leak_rows

    # Price position outliers (most expensive with low share, cheapest with high share)
    needed = ["asinMedianPurchasePrice_amount", "totalMedianPurchasePrice_amount", "asinPurchaseShare"]
    if not query_report.empty and all(c in query_report.columns for c in needed):
        pp = query_report.copy()
        for c in needed + ["searchQueryVolume"]:
            pp[c] = pd.to_numeric(pp[c], errors="coerce").fillna(0)
        pp["price_gap"] = pp["asinMedianPurchasePrice_amount"] - pp["totalMedianPurchasePrice_amount"]
        pp = pp[pp["totalMedianPurchasePrice_amount"] > 0].nlargest(top_n, "searchQueryVolume")

        report["insights"]["price_position"] = [
            {
                "keyword": str(r["searchQuery"]),
                "search_volume": int(r["searchQueryVolume"]),
                "asin_price_usd": round(float(r["asinMedianPurchasePrice_amount"]), 2),
                "market_median_price_usd": round(float(r["totalMedianPurchasePrice_amount"]), 2),
                "price_gap_usd": round(float(r["price_gap"]), 2),
                "purchase_share_pct": round(float(r["asinPurchaseShare"]) * 100, 3),
            }
            for _, r in pp.iterrows()
        ]

    # Keyword momentum (if multi-week)
    if not date_query_report.empty:
        dqr = date_query_report.copy()
        dqr["startDate"] = pd.to_datetime(dqr["startDate"], errors="coerce")
        dates = sorted(dqr["startDate"].dropna().unique())
        if len(dates) >= 2:
            first = dqr[dqr["startDate"] == dates[0]].set_index("searchQuery")
            last = dqr[dqr["startDate"] == dates[-1]].set_index("searchQuery")
            common_keywords = last.nlargest(top_n, "searchQueryVolume").index.tolist()

            momentum = []
            for kw in common_keywords:
                if kw not in first.index:
                    continue
                share_before = _safe_num(first.loc[kw, "asinImpressionShare"])
                share_after = _safe_num(last.loc[kw, "asinImpressionShare"])
                vol = _safe_num(last.loc[kw, "searchQueryVolume"])
                if share_before > 0:
                    change = (share_after - share_before) / share_before * 100
                elif share_after > 0:
                    change = 100
                else:
                    change = 0
                momentum.append({
                    "keyword": str(kw),
                    "search_volume": int(vol),
                    "impression_share_before_pct": round(share_before * 100, 3),
                    "impression_share_after_pct": round(share_after * 100, 3),
                    "share_change_pct": round(change, 1),
                })
            momentum.sort(key=lambda x: abs(x["share_change_pct"]), reverse=True)
            report["insights"]["keyword_momentum"] = momentum

    # Cart abandonment outliers
    if not query_report.empty:
        ab = query_report.copy()
        for c in ["asinCartAddCount", "asinPurchaseCount", "totalCartAddCount", "totalPurchaseCount", "searchQueryVolume"]:
            if c in ab.columns:
                ab[c] = pd.to_numeric(ab[c], errors="coerce").fillna(0)

        def _abandon(atc, pur):
            return round((1 - pur / atc) * 100, 1) if atc else 0

        ab["asin_abandonment"] = ab.apply(lambda r: _abandon(r.get("asinCartAddCount", 0), r.get("asinPurchaseCount", 0)), axis=1)
        ab["market_abandonment"] = ab.apply(lambda r: _abandon(r.get("totalCartAddCount", 0), r.get("totalPurchaseCount", 0)), axis=1)
        ab["abandonment_gap"] = ab["asin_abandonment"] - ab["market_abandonment"]
        ab_top = ab.nlargest(top_n, "searchQueryVolume")

        report["insights"]["cart_abandonment"] = [
            {
                "keyword": str(r["searchQuery"]),
                "search_volume": int(r["searchQueryVolume"]),
                "asin_abandonment_pct": float(r["asin_abandonment"]),
                "market_abandonment_pct": float(r["market_abandonment"]),
                "abandonment_gap_pct": round(float(r["abandonment_gap"]), 1),
            }
            for _, r in ab_top.iterrows()
        ]

    # ---- full data ----
    # Full tables for deep analysis by the agent (capped by top_n to keep size reasonable)
    def _df_to_records(df: pd.DataFrame, limit: int | None = None) -> list:
        if df.empty:
            return []
        d = df.head(limit) if limit else df
        # Convert dates to strings for JSON safety
        d = d.copy()
        for col in d.columns:
            if pd.api.types.is_datetime64_any_dtype(d[col]):
                d[col] = d[col].dt.strftime("%Y-%m-%d")
        return json.loads(d.to_json(orient="records", date_format="iso"))

    report["data"] = {
        "query_report": _df_to_records(query_report, limit=top_n * 3),
        "date_report": _df_to_records(date_report),
        "combined_report": _df_to_records(combined_report),
    }

    return report
