import concurrent.futures
import re

import pandas as pd
import streamlit as st

from modules.sc_modules import get_sku_prices, update_listing_prices

MAX_WORKERS = 10
ASIN_PATTERN = re.compile(r"[A-Z0-9]{10}")


def parse_asins(text: str) -> list[str]:
    if not text:
        return []
    candidates = re.split(r"[\s,;]+", text.strip().upper())
    seen = set()
    asins = []
    for c in candidates:
        c = c.strip()
        if ASIN_PATTERN.fullmatch(c) and c not in seen:
            asins.append(c)
            seen.add(c)
    return asins


def _fmt_money(value, currency: str = "USD") -> str:
    if value is None:
        return "—"
    symbol = "$" if currency == "USD" else f"{currency} "
    try:
        return f"{symbol}{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def _load_prices(asins: list[str], dictionary: pd.DataFrame):
    skus_by_asin = {}
    missing_asins = []
    for asin in asins:
        skus = (
            dictionary.loc[dictionary["asin"] == asin]["sku"]
            .dropna()
            .unique()
            .tolist()
        )
        if skus:
            skus_by_asin[asin] = skus
        else:
            missing_asins.append(asin)

    flat = [(asin, sku) for asin, skus in skus_by_asin.items() for sku in skus]
    sku_results = {}

    if flat:
        progress = st.progress(0.0, text="Reading prices from Amazon...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {
                executor.submit(get_sku_prices, sku): (asin, sku) for asin, sku in flat
            }
            done = 0
            for fut in concurrent.futures.as_completed(future_map):
                asin, sku = future_map[fut]
                try:
                    sku_results[(asin, sku)] = fut.result()
                except Exception as e:
                    sku_results[(asin, sku)] = {
                        "sku": sku,
                        "our_price": None,
                        "list_price": None,
                        "currency": "USD",
                        "product_type": None,
                        "found": False,
                        "error": str(e),
                    }
                done += 1
                progress.progress(
                    done / len(flat), text=f"Reading prices ({done}/{len(flat)})"
                )
        progress.empty()

    data = {
        asin: [sku_results[(asin, sku)] for sku in skus_by_asin[asin]]
        for asin in skus_by_asin
    }
    return data, missing_asins


def _propagate_asin_value(field: str, asin: str, skus: list):
    val = st.session_state.get(f"pricing_asin_{field}_{asin}")
    if val is None:
        return
    for sku in skus:
        st.session_state[f"pricing_sku_{field}_{sku}"] = val


def _toggle_asin(asin: str):
    key = f"pricing_expanded_{asin}"
    st.session_state[key] = not st.session_state.get(key, True)


def _set_all_expanded(value: bool):
    for asin in (st.session_state.get("pricing_data") or {}):
        st.session_state[f"pricing_expanded_{asin}"] = value


def _clear_pricing_state():
    st.session_state.pricing_data = {}
    for k in list(st.session_state.keys()):
        if (
            k.startswith("pricing_sku_")
            or k.startswith("pricing_asin_")
            or k.startswith("pricing_expanded_")
            or k.startswith("pricing_toggle_")
        ):
            del st.session_state[k]


def render_pricing_section(dictionary: pd.DataFrame, visibility: bool):
    with st.expander("Pricing", expanded=False, icon=":material/sell:"):
        st.markdown(
            "Paste ASINs (one per line, or comma/space separated). All SKUs mapped "
            "to each ASIN will load with their current Amazon prices. Setting an "
            "ASIN-level price auto-fills every child SKU; SKU-level entries only "
            "affect that SKU."
        )

        st.text_area(
            "ASINs",
            placeholder="B0XXXXXXXX, B0YYYYYYYY, ...",
            key="pricing_asins_text",
            height=100,
        )

        action_cols = st.columns([1, 1, 1, 1, 1, 3])
        load_clicked = action_cols[0].button(
            "Load prices",
            icon=":material/download:",
            key="pricing_load_btn",
        )

        has_data = bool(st.session_state.get("pricing_data"))

        refresh_clicked = action_cols[1].button(
            "Refresh",
            icon=":material/refresh:",
            key="pricing_refresh_btn",
            disabled=not has_data,
        )
        clear_clicked = action_cols[2].button(
            "Clear",
            icon=":material/clear:",
            key="pricing_clear_btn",
            type="tertiary",
            disabled=not has_data,
        )
        action_cols[3].button(
            "Expand all",
            icon=":material/unfold_more:",
            key="pricing_expand_all_btn",
            type="tertiary",
            disabled=not has_data,
            on_click=_set_all_expanded,
            args=(True,),
        )
        action_cols[4].button(
            "Collapse all",
            icon=":material/unfold_less:",
            key="pricing_collapse_all_btn",
            type="tertiary",
            disabled=not has_data,
            on_click=_set_all_expanded,
            args=(False,),
        )

        notice_area = st.container()

        if load_clicked:
            asins = parse_asins(st.session_state.get("pricing_asins_text", ""))
            if not asins:
                notice_area.warning("No valid ASINs found in input.")
            else:
                data, missing = _load_prices(asins, dictionary)
                st.session_state.pricing_data = data
                if missing:
                    notice_area.warning(
                        f"ASINs not found in dictionary: {', '.join(missing)}"
                    )
                if not data:
                    notice_area.error("No matching SKUs found for any ASIN.")
                has_data = bool(data)

        if refresh_clicked and has_data:
            asins = list(st.session_state.pricing_data.keys())
            data, _missing = _load_prices(asins, dictionary)
            st.session_state.pricing_data = data

        if clear_clicked:
            _clear_pricing_state()
            st.rerun()

        if not st.session_state.get("pricing_data"):
            return

        rows_area = st.container()
        push_area = st.container()
        push_status_area = st.container()

        col_widths = [0.4, 2.6, 2, 2, 2, 2]
        hcols = rows_area.columns(col_widths)
        hcols[0].markdown("")
        hcols[1].markdown("**ASIN / SKU**")
        hcols[2].markdown("**Current our_price**")
        hcols[3].markdown("**Current list_price**")
        hcols[4].markdown("**New our_price**")
        hcols[5].markdown("**New list_price**")

        for asin, sku_rows in st.session_state.pricing_data.items():
            child_skus = [r["sku"] for r in sku_rows]
            expanded_key = f"pricing_expanded_{asin}"
            if expanded_key not in st.session_state:
                st.session_state[expanded_key] = True
            expanded = st.session_state[expanded_key]

            acols = rows_area.columns(col_widths)
            acols[0].button(
                "",
                icon=(
                    ":material/keyboard_arrow_down:"
                    if expanded
                    else ":material/chevron_right:"
                ),
                key=f"pricing_toggle_{asin}",
                type="tertiary",
                on_click=_toggle_asin,
                args=(asin,),
                help="Show/hide child SKUs",
            )
            acols[1].markdown(
                f"[**{asin}**](https://www.amazon.com/dp/{asin}) "
                f"— *applies to all {len(child_skus)} SKU(s)*"
            )
            acols[2].markdown("—")
            acols[3].markdown("—")
            acols[4].number_input(
                label=f"asin our_price {asin}",
                label_visibility="collapsed",
                key=f"pricing_asin_our_{asin}",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=None,
                placeholder="set all SKUs",
                on_change=_propagate_asin_value,
                args=("our", asin, child_skus),
                disabled=not visibility,
            )
            acols[5].number_input(
                label=f"asin list_price {asin}",
                label_visibility="collapsed",
                key=f"pricing_asin_list_{asin}",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=None,
                placeholder="set all SKUs",
                on_change=_propagate_asin_value,
                args=("list", asin, child_skus),
                disabled=not visibility,
            )

            if not expanded:
                continue

            for row in sku_rows:
                sku = row["sku"]
                currency = row.get("currency") or "USD"
                scols = rows_area.columns(col_widths)
                scols[0].markdown("")
                scols[1].markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;`{sku}`", unsafe_allow_html=True
                )
                if not row.get("found", True):
                    scols[2].markdown(":orange[not found]")
                    scols[3].markdown(":orange[—]")
                else:
                    scols[2].markdown(_fmt_money(row.get("our_price"), currency))
                    scols[3].markdown(_fmt_money(row.get("list_price"), currency))
                scols[4].number_input(
                    label=f"sku our_price {sku}",
                    label_visibility="collapsed",
                    key=f"pricing_sku_our_{sku}",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=None,
                    disabled=not visibility,
                )
                scols[5].number_input(
                    label=f"sku list_price {sku}",
                    label_visibility="collapsed",
                    key=f"pricing_sku_list_{sku}",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=None,
                    disabled=not visibility,
                )

        if push_area.button(
            "Push prices to Amazon",
            icon=":material/arrow_upward:",
            disabled=not visibility,
            type="primary",
            key="pricing_push_btn",
        ):
            push_jobs = []
            skipped_no_type = []
            for asin, sku_rows in st.session_state.pricing_data.items():
                for row in sku_rows:
                    sku = row["sku"]
                    new_our = st.session_state.get(f"pricing_sku_our_{sku}")
                    new_list = st.session_state.get(f"pricing_sku_list_{sku}")
                    if new_our is None and new_list is None:
                        continue
                    if not row.get("product_type"):
                        skipped_no_type.append(sku)
                        continue
                    push_jobs.append(
                        {
                            "sku": sku,
                            "product_type": row["product_type"],
                            "our_price": new_our,
                            "list_price": new_list,
                            "currency": row.get("currency") or "USD",
                        }
                    )

            if skipped_no_type:
                push_status_area.error(
                    "No product type known (load failed?). Skipping: "
                    + ", ".join(skipped_no_type)
                )

            if not push_jobs:
                push_status_area.warning(
                    "Nothing to push — no new prices entered."
                )
            else:
                progress = push_status_area.progress(0.0, text="Pushing prices...")
                results = []
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=MAX_WORKERS
                ) as executor:
                    futures = [
                        executor.submit(
                            update_listing_prices,
                            sku=job["sku"],
                            product_type=job["product_type"],
                            our_price=job["our_price"],
                            list_price=job["list_price"],
                            currency=job["currency"],
                        )
                        for job in push_jobs
                    ]
                    done = 0
                    for fut in concurrent.futures.as_completed(futures):
                        results.append(fut.result())
                        done += 1
                        progress.progress(
                            done / len(futures),
                            text=f"Pushing ({done}/{len(futures)})",
                        )
                progress.empty()

                successes = [r for r in results if r.startswith("SUCCESS")]
                errors = [r for r in results if r.startswith("ERROR")]
                if successes:
                    push_status_area.success(
                        f"Pushed {len(successes)}/{len(results)}:\n\n"
                        + "\n\n".join(successes)
                    )
                if errors:
                    push_status_area.error(
                        f"{len(errors)} error(s):\n\n" + "\n\n".join(errors)
                    )
                push_status_area.info(
                    "Click **Refresh** to re-read current prices from Amazon and verify."
                )
