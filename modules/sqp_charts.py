import random

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts


def line_charts():
    st.header("Line Charts")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Basic Line")
        options_basic = {
            "xAxis": {
                "type": "category",
                "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            },
            "yAxis": {"type": "value"},
            "series": [{"data": [150, 230, 224, 218, 135, 147, 260], "type": "line"}],
        }
        st_echarts(options=options_basic, height="400px")

    with col2:
        st.subheader("Smoothed Line")
        options_smooth = {
            "xAxis": {
                "type": "category",
                "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            },
            "yAxis": {"type": "value"},
            "series": [
                {
                    "data": [150, 230, 224, 218, 135, 147, 260],
                    "type": "line",
                    "smooth": True,
                }
            ],
        }
        st_echarts(options=options_smooth, height="400px")
        return options_smooth


def area_charts():
    st.subheader("Stacked Area Chart")
    options_area = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross", "label": {"backgroundColor": "#6a7985"}},
        },
        "legend": {
            "data": ["Email", "Union Ads", "Video Ads", "Direct", "Search Engine"]
        },
        "toolbox": {"feature": {"saveAsImage": {}}},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": [
            {
                "type": "category",
                "boundaryGap": False,
                "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            }
        ],
        "yAxis": [{"type": "value"}],
        "series": [
            {
                "name": "Email",
                "type": "line",
                "stack": "Total",
                "areaStyle": {},
                "emphasis": {"focus": "series"},
                "data": [120, 132, 101, 134, 90, 230, 210],
            },
            {
                "name": "Union Ads",
                "type": "line",
                "stack": "Total",
                "areaStyle": {},
                "emphasis": {"focus": "series"},
                "data": [220, 182, 191, 234, 290, 330, 310],
            },
            {
                "name": "Video Ads",
                "type": "line",
                "stack": "Total",
                "areaStyle": {},
                "emphasis": {"focus": "series"},
                "data": [150, 232, 201, 154, 190, 330, 410],
            },
            {
                "name": "Direct",
                "type": "line",
                "stack": "Total",
                "areaStyle": {},
                "emphasis": {"focus": "series"},
                "data": [320, 332, 301, 334, 390, 330, 320],
            },
            {
                "name": "Search Engine",
                "type": "line",
                "stack": "Total",
                "label": {"show": True, "position": "top"},
                "areaStyle": {},
                "emphasis": {"focus": "series"},
                "data": [820, 932, 901, 934, 1290, 1330, 1320],
            },
        ],
    }
    st_echarts(options=options_area, height="400px")
    return options_area


def bar_charts():
    st.header("Bar Charts")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Basic Bar")
        options_basic = {
            "xAxis": {
                "type": "category",
                "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            },
            "yAxis": {"type": "value"},
            "series": [{"data": [120, 200, 150, 80, 70, 110, 130], "type": "bar"}],
        }
        st_echarts(options=options_basic, height="400px")

    with col2:
        st.subheader("Bar with Background")
        options_bg = {
            "xAxis": {
                "type": "category",
                "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            },
            "yAxis": {"type": "value"},
            "series": [
                {
                    "data": [120, 200, 150, 80, 70, 110, 130],
                    "type": "bar",
                    "showBackground": True,
                    "backgroundStyle": {"color": "rgba(180, 180, 180, 0.2)"},
                }
            ],
        }
        st_echarts(options=options_bg, height="400px")

    st.subheader("Stacked Bar Chart")
    options_stacked = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "value"},
        "yAxis": {
            "type": "category",
            "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        },
        "series": [
            {
                "name": "Direct",
                "type": "bar",
                "stack": "total",
                "label": {"show": True},
                "emphasis": {"focus": "series"},
                "data": [320, 302, 301, 334, 390, 330, 320],
            },
            {
                "name": "Mail Ad",
                "type": "bar",
                "stack": "total",
                "label": {"show": True},
                "emphasis": {"focus": "series"},
                "data": [120, 132, 101, 134, 90, 230, 210],
            },
            {
                "name": "Affiliate Ad",
                "type": "bar",
                "stack": "total",
                "label": {"show": True},
                "emphasis": {"focus": "series"},
                "data": [220, 182, 191, 234, 290, 330, 310],
            },
            {
                "name": "Video Ad",
                "type": "bar",
                "stack": "total",
                "label": {"show": True},
                "emphasis": {"focus": "series"},
                "data": [150, 212, 201, 154, 190, 330, 410],
            },
            {
                "name": "Search Engine",
                "type": "bar",
                "stack": "total",
                "label": {"show": True},
                "emphasis": {"focus": "series"},
                "data": [820, 832, 901, 934, 1290, 1330, 1320],
            },
        ],
    }
    st_echarts(options=options_stacked, height="500px")


def pie_charts():
    st.header("Pie Charts")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Basic Pie")
        options_pie = {
            "title": {
                "text": "Referer of a Website",
                "subtext": "Fake Data",
                "left": "center",
            },
            "tooltip": {"trigger": "item"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [
                {
                    "name": "Access From",
                    "type": "pie",
                    "radius": "50%",
                    "data": [
                        {"value": 1048, "name": "Search Engine"},
                        {"value": 735, "name": "Direct"},
                        {"value": 580, "name": "Email"},
                        {"value": 484, "name": "Union Ads"},
                        {"value": 300, "name": "Video Ads"},
                    ],
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)",
                        }
                    },
                }
            ],
        }
        st_echarts(options=options_pie, height="400px")

    with col2:
        st.subheader("Doughnut Chart")
        options_doughnut = {
            "tooltip": {"trigger": "item"},
            "legend": {"top": "5%", "left": "center"},
            "series": [
                {
                    "name": "Access From",
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "avoidLabelOverlap": False,
                    "itemStyle": {
                        "borderRadius": 10,
                        "borderColor": "#fff",
                        "borderWidth": 2,
                    },
                    "label": {"show": False, "position": "center"},
                    "emphasis": {
                        "label": {"show": True, "fontSize": "40", "fontWeight": "bold"}
                    },
                    "labelLine": {"show": False},
                    "data": [
                        {"value": 1048, "name": "Search Engine"},
                        {"value": 735, "name": "Direct"},
                        {"value": 580, "name": "Email"},
                        {"value": 484, "name": "Union Ads"},
                        {"value": 300, "name": "Video Ads"},
                    ],
                }
            ],
        }
        st_echarts(options=options_doughnut, height="400px")

    st.subheader("Nightingale Rose Chart")
    options_rose = {
        "legend": {"top": "bottom"},
        "toolbox": {
            "show": True,
            "feature": {
                "mark": {"show": True},
                "dataView": {"show": True, "readOnly": False},
                "restore": {"show": True},
                "saveAsImage": {"show": True},
            },
        },
        "series": [
            {
                "name": "Nightingale Chart",
                "type": "pie",
                "radius": [50, 250],
                "center": ["50%", "50%"],
                "roseType": "area",
                "itemStyle": {"borderRadius": 8},
                "data": [
                    {"value": 40, "name": "rose 1"},
                    {"value": 38, "name": "rose 2"},
                    {"value": 32, "name": "rose 3"},
                    {"value": 30, "name": "rose 4"},
                    {"value": 28, "name": "rose 5"},
                    {"value": 26, "name": "rose 6"},
                    {"value": 22, "name": "rose 7"},
                    {"value": 18, "name": "rose 8"},
                ],
            }
        ],
    }
    st_echarts(options=options_rose, height="600px")


def scatter_charts(x_axis, y_axis, series: list):
    """Example of the series:
    series = [
        {
            "name": "Click Price",
            "type": "scatter",
            "data": total_click_data,
            "itemStyle": {"color": "#5470c6", "opacity": 0.5},  # Blue
        },
        {
            "name": "ATC Price",
            "type": "scatter",
            "data": total_atc_data,
            "itemStyle": {"color": "#91cc75", "opacity": 0.5},  # Green
        },
        {
            "name": "Purchase Price",
            "type": "scatter",
            "data": total_purchase_data,
            "itemStyle": {"color": "#fac858", "opacity": 0.5},  # Yellow/Orange
        },
    ]
    """

    all_data = [x[2] for part in series for x in part["data"]]
    min_vol, max_vol = min(all_data), max(all_data)

    options_bubble = {
        "legend": {"data": ["Click Price", "ATC Price", "Purchase Price"], "top": "5%"},
        "xAxis": {"type": "time", "name": "Date"},
        "yAxis": {"type": "value", "name": "Price ($)"},
        "visualMap": {
            "show": False,  # Hide the legend for size if you want it clean
            "dimension": 2,  # Use the 3rd element (Search Volume) for size
            "min": min_vol,
            "max": max_vol,
            "inRange": {"symbolSize": [10, 70]},  # Bubbles scale from 10px to 70px
        },
        "series": series,
        "tooltip": {"trigger": "item"},
    }
    return options_bubble


def radar_charts(df: pd.DataFrame):
    if len(df) == 0:
        return
    cols = [
        ["searchQueryVolume", "asinImpressionCount"],
        ["totalCTR", "asinCTR"],
        ["totalClickToAtcConversion", "asinClickToAtcConversion"],
        ["totalConversion", "asinConversion"],
    ]
    niche_cols = [x[0] for x in cols]
    asin_cols = [x[1] for x in cols]

    df_normalized = df[niche_cols + asin_cols].copy()
    df_normalized["asinImpressionCount"] = (
        df_normalized["asinImpressionCount"] / df_normalized["searchQueryVolume"]
    )
    df_normalized["searchQueryVolume"] = 1

    for c in df_normalized.columns:
        df_normalized[c] = round(df_normalized[c] * 100, 3)

    niche_values = df_normalized.loc[:, niche_cols].iloc[0].astype(float).tolist()
    asin_values = df_normalized.loc[:, asin_cols].iloc[0].astype(float).tolist()

    local_max = {
        col_names[0]: df_normalized[col_names].max(axis=1).iloc[0] * 1.1
        for col_names in cols
    }

    options_radar = {
        "title": {
            "text": "ASIN vs Niche performance",
            "top": "0%",  # Keeps title at the very top
            "left": "center",
        },
        "legend": {
            "data": ["Niche", "ASIN"],
            "bottom": "2%",  # Moves legend to the bottom to clear space
        },
        "tooltip": {"trigger": "item"},
        "radar": {
            "indicator": [
                {"name": "Views", "max": local_max["searchQueryVolume"]},
                {"name": "CTR", "max": local_max["totalCTR"]},
                {
                    "name": "ATC conversion",
                    "max": local_max["totalClickToAtcConversion"],
                },
                {"name": "Conversion", "max": local_max["totalConversion"]},
            ],
            "center": [
                "50%",
                "48%",
            ],
            "radius": "65%",
            "splitNumber": 5,
            "axisLine": {"show": True},
            "shape": "polygon",
        },
        "series": [
            {
                "name": "Search performance against the niche",
                "type": "radar",
                "data": [
                    {
                        "value": niche_values,
                        "name": "Niche",
                    },
                    {
                        "value": asin_values,
                        "name": "ASIN",
                    },
                ],
            }
        ],
    }
    return options_radar


def candle_charts():
    st.header("Candlestick Chart")
    options_candle = {
        "xAxis": {"data": ["2017-10-24", "2017-10-25", "2017-10-26", "2017-10-27"]},
        "yAxis": {},
        "series": [
            {
                "type": "candlestick",
                "data": [
                    [20, 34, 10, 38],
                    [40, 35, 30, 50],
                    [31, 38, 33, 44],
                    [38, 15, 5, 42],
                ],
            }
        ],
    }
    st_echarts(options=options_candle, height="500px")


def boxplot_charts():
    st.header("Boxplot")
    options_box = {
        "title": {"text": "Basic Boxplot"},
        "dataset": [
            {
                "source": [
                    [
                        850,
                        740,
                        900,
                        1070,
                        930,
                        850,
                        950,
                        980,
                        980,
                        880,
                        1000,
                        980,
                        930,
                        650,
                        760,
                        810,
                        1000,
                        1000,
                        960,
                        960,
                    ],
                    [
                        960,
                        940,
                        960,
                        940,
                        880,
                        800,
                        850,
                        880,
                        900,
                        840,
                        830,
                        790,
                        810,
                        880,
                        880,
                        830,
                        800,
                        790,
                        760,
                        800,
                    ],
                ]
            },
            {
                "transform": {
                    "type": "boxplot",
                    "config": {"itemNameFormatter": "expr {value}"},
                }
            },
        ],
        "tooltip": {"trigger": "item", "axisPointer": {"type": "shadow"}},
        "grid": {"left": "10%", "right": "10%", "bottom": "15%"},
        "xAxis": {
            "type": "category",
            "boundaryGap": True,
            "nameGap": 30,
            "splitArea": {"show": False},
            "splitLine": {"show": False},
        },
        "yAxis": {"type": "value", "name": "Value", "splitArea": {"show": True}},
        "series": [{"name": "boxplot", "type": "boxplot", "datasetIndex": 1}],
    }
    st_echarts(options=options_box, height="500px")


def heatmap_charts():
    st.header("Heatmap")
    hours = [
        "12a",
        "1a",
        "2a",
        "3a",
        "4a",
        "5a",
        "6a",
        "7a",
        "8a",
        "9a",
        "10a",
        "11a",
        "12p",
        "1p",
        "2p",
        "3p",
        "4p",
        "5p",
        "6p",
        "7p",
        "8p",
        "9p",
        "10p",
        "11p",
    ]
    days = [
        "Saturday",
        "Friday",
        "Thursday",
        "Wednesday",
        "Tuesday",
        "Monday",
        "Sunday",
    ]
    data = [[i, j, random.randint(0, 10)] for i in range(24) for j in range(7)]
    options_heatmap = {
        "tooltip": {"position": "top"},
        "grid": {"height": "50%", "top": "10%"},
        "xAxis": {"type": "category", "data": hours, "splitArea": {"show": True}},
        "yAxis": {"type": "category", "data": days, "splitArea": {"show": True}},
        "visualMap": {
            "min": 0,
            "max": 10,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "15%",
        },
        "series": [
            {
                "name": "Punch Card",
                "type": "heatmap",
                "data": data,
                "label": {"show": True},
                "emphasis": {
                    "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"}
                },
            }
        ],
    }
    st_echarts(options=options_heatmap, height="500px")


def graph_charts():
    st.header("Graph (Network)")
    options_graph = {
        "title": {"text": "Basic Graph"},
        "tooltip": {},
        "animationDurationUpdate": 1500,
        "animationEasingUpdate": "quinticInOut",
        "series": [
            {
                "type": "graph",
                "layout": "none",
                "symbolSize": 50,
                "roam": True,
                "label": {"show": True},
                "edgeSymbol": ["circle", "arrow"],
                "edgeSymbolSize": [4, 10],
                "edgeLabel": {"fontSize": 20},
                "data": [
                    {"name": "Node 1", "x": 300, "y": 300},
                    {"name": "Node 2", "x": 800, "y": 300},
                    {"name": "Node 3", "x": 550, "y": 100},
                    {"name": "Node 4", "x": 550, "y": 500},
                ],
                "links": [
                    {
                        "source": 0,
                        "target": 1,
                        "symbolSize": [5, 20],
                        "label": {"show": True},
                    },
                    {"source": 1, "target": 2, "label": {"show": True}},
                    {"source": 2, "target": 0},
                    {"source": 2, "target": 3},
                ],
                "lineStyle": {"opacity": 0.9, "width": 2, "curveness": 0},
            }
        ],
    }
    st_echarts(options=options_graph, height="500px")


def treee_charts():
    st.header("Tree Chart")
    data_tree = {
        "name": "flare",
        "children": [
            {
                "name": "analytics",
                "children": [
                    {
                        "name": "cluster",
                        "children": [
                            {"name": "AgglomerativeCluster", "value": 3938},
                            {"name": "CommunityStructure", "value": 3812},
                            {"name": "HierarchicalCluster", "value": 6714},
                            {"name": "MergeEdge", "value": 743},
                        ],
                    },
                    {
                        "name": "graph",
                        "children": [
                            {"name": "BetweennessCentrality", "value": 3534},
                            {"name": "LinkDistance", "value": 5731},
                            {"name": "MaxFlowMinCut", "value": 7840},
                            {"name": "ShortestPaths", "value": 5914},
                            {"name": "SpanningTree", "value": 3416},
                        ],
                    },
                ],
            }
        ],
    }
    options_tree = {
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [
            {
                "type": "tree",
                "data": [data_tree],
                "top": "1%",
                "left": "7%",
                "bottom": "1%",
                "right": "20%",
                "symbolSize": 7,
                "label": {
                    "position": "left",
                    "verticalAlign": "middle",
                    "align": "right",
                    "fontSize": 9,
                },
                "leaves": {
                    "label": {
                        "position": "right",
                        "verticalAlign": "middle",
                        "align": "left",
                    }
                },
                "emphasis": {"focus": "descendant"},
                "expandAndCollapse": True,
                "animationDuration": 550,
                "animationDurationUpdate": 750,
            }
        ],
    }
    st_echarts(options=options_tree, height="500px")


def treemap_charts():
    st.header("Treemap")
    options_treemap = {
        "series": [
            {
                "type": "treemap",
                "data": [
                    {
                        "name": "nodeA",
                        "value": 10,
                        "children": [
                            {"name": "nodeAa", "value": 4},
                            {"name": "nodeAb", "value": 6},
                        ],
                    },
                    {
                        "name": "nodeB",
                        "value": 20,
                        "children": [
                            {
                                "name": "nodeBa",
                                "value": 20,
                                "children": [{"name": "nodeBa1", "value": 20}],
                            }
                        ],
                    },
                ],
            }
        ]
    }
    st_echarts(options=options_treemap, height="500px")


def sunburst_charts():
    st.header("Sunburst")
    data_sunburst = [
        {
            "name": "Grandpa",
            "children": [
                {
                    "name": "Uncle Leo",
                    "value": 15,
                    "children": [
                        {"name": "Cousin Jack", "value": 2},
                        {
                            "name": "Cousin Mary",
                            "value": 5,
                            "children": [{"name": "Jackson", "value": 2}],
                        },
                    ],
                },
                {"name": "Aunt Jane", "children": [{"name": "Cousin Ben", "value": 4}]},
            ],
        },
        {
            "name": "Nancy",
            "children": [
                {
                    "name": "Uncle Nike",
                    "children": [
                        {"name": "Cousin Betty", "value": 1},
                        {"name": "Cousin Jenny", "value": 2},
                    ],
                }
            ],
        },
    ]
    options_sunburst = {
        "series": {
            "type": "sunburst",
            "data": data_sunburst,
            "radius": [0, "90%"],
            "label": {"rotate": "radial"},
        }
    }
    st_echarts(options=options_sunburst, height="500px")


def sankey_charts():
    st.header("Sankey Diagram")
    options_sankey = {
        "series": {
            "type": "sankey",
            "layout": "none",
            "emphasis": {"focus": "adjacency"},
            "data": [
                {"name": "a"},
                {"name": "b"},
                {"name": "a1"},
                {"name": "a2"},
                {"name": "b1"},
                {"name": "c"},
            ],
            "links": [
                {"source": "a", "target": "a1", "value": 5},
                {"source": "a", "target": "a2", "value": 3},
                {"source": "b", "target": "b1", "value": 8},
                {"source": "a", "target": "b1", "value": 3},
                {"source": "b1", "target": "a1", "value": 1},
                {"source": "b1", "target": "c", "value": 2},
            ],
        }
    }
    st_echarts(options=options_sankey, height="500px")


def funnel_charts():
    st.header("Funnel Chart")
    options_funnel = {
        "title": {"text": "Funnel"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c}%"},
        "toolbox": {
            "feature": {
                "dataView": {"readOnly": False},
                "restore": {},
                "saveAsImage": {},
            }
        },
        "legend": {"data": ["Show", "Click", "Visit", "Inquiry", "Order"]},
        "series": [
            {
                "name": "Funnel",
                "type": "funnel",
                "left": "10%",
                "top": 60,
                "bottom": 60,
                "width": "80%",
                "min": 0,
                "max": 100,
                "minSize": "0%",
                "maxSize": "100%",
                "sort": "descending",
                "gap": 2,
                "label": {"show": True, "position": "inside"},
                "labelLine": {"length": 10, "lineStyle": {"width": 1, "type": "solid"}},
                "itemStyle": {"borderColor": "#fff", "borderWidth": 1},
                "emphasis": {"label": {"fontSize": 20}},
                "data": [
                    {"value": 60, "name": "Visit"},
                    {"value": 40, "name": "Inquiry"},
                    {"value": 20, "name": "Order"},
                    {"value": 80, "name": "Click"},
                    {"value": 100, "name": "Show"},
                ],
            }
        ],
    }
    st_echarts(options=options_funnel, height="500px")


def gauge_charts():
    st.header("Gauge")
    options_gauge = {
        "tooltip": {"formatter": "{a} <br/>{b} : {c}%"},
        "series": [
            {
                "name": "Pressure",
                "type": "gauge",
                "progress": {"show": True},
                "detail": {"valueAnimation": True, "formatter": "{value}"},
                "data": [{"value": 50, "name": "SCORE"}],
            }
        ],
    }
    st_echarts(options=options_gauge, height="500px")


def theme_river_charts():
    st.header("Theme River (Streamgraph)")
    options_river = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "line",
                "lineStyle": {"color": "rgba(0,0,0,0.2)", "width": 1, "type": "solid"},
            },
        },
        "legend": {"data": ["DQ", "TY", "SS", "QG", "SY", "DD"]},
        "singleAxis": {
            "top": 50,
            "bottom": 50,
            "axisTick": {},
            "axisLabel": {},
            "type": "time",
            "axisPointer": {"animation": True, "label": {"show": True}},
            "splitLine": {
                "show": True,
                "lineStyle": {"type": "dashed", "opacity": 0.2},
            },
        },
        "series": [
            {
                "type": "themeRiver",
                "emphasis": {
                    "itemStyle": {"shadowBlur": 20, "shadowColor": "rgba(0, 0, 0, 0.8)"}
                },
                "data": [
                    ["2015/11/08", 10, "DQ"],
                    ["2015/11/09", 15, "DQ"],
                    ["2015/11/10", 35, "DQ"],
                    ["2015/11/11", 38, "DQ"],
                    ["2015/11/12", 22, "DQ"],
                    ["2015/11/13", 16, "DQ"],
                    ["2015/11/14", 7, "DQ"],
                    ["2015/11/08", 35, "TY"],
                    ["2015/11/09", 36, "TY"],
                    ["2015/11/10", 37, "TY"],
                    ["2015/11/11", 22, "TY"],
                    ["2015/11/12", 24, "TY"],
                    ["2015/11/13", 26, "TY"],
                    ["2015/11/14", 34, "TY"],
                    ["2015/11/08", 21, "SS"],
                    ["2015/11/09", 25, "SS"],
                    ["2015/11/10", 27, "SS"],
                    ["2015/11/11", 23, "SS"],
                    ["2015/11/12", 24, "SS"],
                    ["2015/11/13", 21, "SS"],
                    ["2015/11/14", 35, "SS"],
                ],
            }
        ],
    }
    st_echarts(options=options_river, height="400px")


def calendar_charts():
    st.header("Calendar Heatmap")

    def get_virtual_data(year):
        date_list = []
        import datetime

        start = datetime.date(int(year), 1, 1)
        end = datetime.date(int(year) + 1, 1, 1)
        delta = datetime.timedelta(days=1)
        current = start
        while current < end:
            date_list.append([current.strftime("%Y-%m-%d"), random.randint(1, 10000)])
            current += delta
        return date_list

    options_cal = {
        "title": {"top": 30, "left": "center", "text": "Daily Step Count"},
        "tooltip": {},
        "visualMap": {
            "min": 0,
            "max": 10000,
            "type": "piecewise",
            "orient": "horizontal",
            "left": "center",
            "top": 65,
        },
        "calendar": {
            "top": 120,
            "left": 30,
            "right": 30,
            "cellSize": ["auto", 13],
            "range": "2017",
            "itemStyle": {"borderWidth": 0.5},
        },
        "series": {
            "type": "heatmap",
            "coordinateSystem": "calendar",
            "data": get_virtual_data("2017"),
        },
    }
    st_echarts(options=options_cal, height="400px")


def parallel_coordinates_charts(df: pd.DataFrame) -> dict | None:
    if len(df) == 0:
        return
    cols = [
        "searchQueryVolume",
        "totalClickCount",
        "asinClickCount",
        "totalCartAddCount",
        "asinCartAddCount",
        "totalPurchaseCount",
        "asinPurchaseCount",
        "totalConversion",
        "asinConversion",
    ]

    series_data = [
        {"value": row[cols].tolist(), "name": str(row["searchQuery"])}
        for _, row in df.iterrows()
    ]

    limits = {col: df[col].max() * 1.1 for col in cols}
    mid_point = limits["searchQueryVolume"] / 10 / 2
    max_val = limits["searchQueryVolume"] / 5

    options_parallel = {
        "tooltip": {
            "trigger": "item",
        },
        "toolbox": {
            "feature": {
                "dataView": {"readOnly": True, "show": True},
                "restore": {},
                "saveAsImage": {},
            }
        },
        "parallelAxis": [
            {"dim": 0, "name": "Search Volume", "max": limits["searchQueryVolume"]},
            {"dim": 1, "name": "Total Click Count", "max": limits["totalClickCount"]},
            {"dim": 2, "name": "ASIN click count", "max": limits["asinClickCount"]},
            {
                "dim": 3,
                "name": "Total Cart Add Count",
                "max": limits["totalCartAddCount"],
            },
            {
                "dim": 4,
                "name": "ASIN Cart Add Count",
                "max": limits["asinCartAddCount"],
            },
            {
                "dim": 5,
                "name": "Total Purchase Count",
                "max": limits["totalPurchaseCount"],
            },
            {
                "dim": 6,
                "name": "ASIN Purchase Count",
                "max": limits["asinPurchaseCount"],
            },
            {"dim": 7, "name": "Total Conversion", "max": limits["totalConversion"]},
            {"dim": 8, "name": "ASIN Conversion", "max": limits["asinConversion"]},
        ],
        "parallel": {
            "left": "5%",
            "right": "15%",
            "bottom": "10%",
            "parallelAxisDefault": {
                "type": "value",
                "nameLocation": "end",
                "nameGap": 20,
                "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            },
        },
        "visualMap": {
            "show": True,
            "type": "continuous",
            "dimension": 0,  # Search Volume
            "pieces": [
                {
                    "gt": mid_point,
                    "lte": max_val,
                    "color": "#00d4ff",
                    "label": "Top Tier",
                },
                {"gt": 0, "lte": mid_point, "color": "#ff4500", "label": "Low Tier"},
            ],
            # "min": 0,
            # "max": limits["searchQueryVolume"] / 10,
            "inRange": {"color": ["#ff4500", "#e68b39", "#00d4ff"]},
        },
        "series": [
            {
                "type": "parallel",
                "lineStyle": {"width": 1.5, "opacity": 0.4},
                "inactiveOpacity": 0.05,
                "activeOpacity": 1,
                "smooth": True,
                "data": series_data,  # Data is now here, not in 'dataset'
            }
        ],
    }

    return options_parallel


def polar_charts():
    st.header("Polar Charts")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Polar Bar")
        options_polar_bar = {
            "angleAxis": {
                "type": "category",
                "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "z": 10,
            },
            "radiusAxis": {},
            "polar": {},
            "series": [
                {
                    "type": "bar",
                    "data": [1, 2, 3, 4, 3, 5, 1],
                    "coordinateSystem": "polar",
                    "name": "A",
                    "stack": "a",
                    "emphasis": {"focus": "series"},
                },
                {
                    "type": "bar",
                    "data": [2, 4, 6, 1, 3, 2, 1],
                    "coordinateSystem": "polar",
                    "name": "B",
                    "stack": "a",
                    "emphasis": {"focus": "series"},
                },
                {
                    "type": "bar",
                    "data": [1, 2, 3, 4, 1, 2, 5],
                    "coordinateSystem": "polar",
                    "name": "C",
                    "stack": "a",
                    "emphasis": {"focus": "series"},
                },
            ],
            "legend": {"show": True, "data": ["A", "B", "C"]},
        }
        st_echarts(options=options_polar_bar, height="400px")

    with col2:
        st.subheader("Polar Scatter")
        data_polar_scatter = [
            [random.randint(0, 100), random.randint(0, 360)] for _ in range(100)
        ]
        options_polar_scatter = {
            "polar": {},
            "angleAxis": {"type": "value", "startAngle": 0},
            "radiusAxis": {"min": 0},
            "series": [
                {
                    "coordinateSystem": "polar",
                    "name": "scatter",
                    "type": "scatter",
                    "symbolSize": 10,
                    "data": data_polar_scatter,
                }
            ],
        }
        st_echarts(options=options_polar_scatter, height="400px")
