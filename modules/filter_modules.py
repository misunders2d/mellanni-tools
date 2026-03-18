import pandas as pd
import streamlit as st
from fuzzywuzzy import fuzz

from modules import gcloud_modules as gc


def is_similar(query, target, threshold: int = 70):
    """Check if the query is similar to the target string using fuzzy matching."""
    if not query or not target:
        return False
    words = query.lower().split()
    targets = target.lower().split()

    if all(
        [
            any([fuzz.ratio(search_term, word) >= threshold for word in words])
            for search_term in targets
        ]
    ):
        return True
    return False


def filter_dictionary(
    coll_target=None, size_target=None, color_target=None, clear_btn_target=None
):
    """
    Filters the dictionary based on selected collection, size or color
    """
    coll_target = coll_target if coll_target else st
    size_target = size_target if size_target else st
    color_target = color_target if color_target else st

    def clear_selection():
        for key in ["sel_col", "sel_size", "sel_color"]:
            st.session_state[key] = []

    if "dictionary" not in st.session_state:
        st.session_state.dictionary = gc.pull_dictionary()
    df = st.session_state.dictionary.copy()
    # Initialize session state keys if they don't exist
    for key in ["sel_col", "sel_size", "sel_color"]:
        if key not in st.session_state:
            st.session_state[key] = []

    # Options for Collection (filtered by Size & Color)
    mask_col = df.copy()
    if st.session_state.sel_size:
        mask_col = mask_col[mask_col["size"].isin(st.session_state.sel_size)]
    if st.session_state.sel_color:
        mask_col = mask_col[mask_col.loc[:, "color"].isin(st.session_state.sel_color)]
    opt_col = sorted(pd.unique(mask_col["collection"]))

    # Options for Size (filtered by Collection & Color)
    mask_size = df.copy()
    if st.session_state.sel_col:
        mask_size = mask_size[mask_size["collection"].isin(st.session_state.sel_col)]
    if st.session_state.sel_color:
        mask_size = mask_size[
            mask_size.loc[:, "color"].isin(st.session_state.sel_color)
        ]
    opt_size = sorted(pd.unique(mask_size["size"]))

    # Options for Color (filtered by Collection & Size)
    mask_color = df.copy()
    if st.session_state.sel_col:
        mask_color = mask_color[mask_color["collection"].isin(st.session_state.sel_col)]
    if st.session_state.sel_size:
        mask_color = mask_color[
            mask_color.loc[:, "size"].isin(st.session_state.sel_size)
        ]
    opt_color = sorted(pd.unique(mask_color["color"]))

    # --- 2. Render the Widgets ---
    coll_target.multiselect(
        "Collections",
        options=opt_col,
        key="sel_col",
        placeholder="Select collection(s)",
    )
    size_target.multiselect(
        "Sizes", options=opt_size, key="sel_size", placeholder="Select size(s)"
    )
    color_target.multiselect(
        "Colors", options=opt_color, key="sel_color", placeholder="Select color(s)"
    )
    if clear_btn_target:

        clear_btn_target.button("Clear selection", on_click=clear_selection)

    # --- 3. Return the Final Filtered DataFrame ---
    final_df = df.copy()
    if st.session_state.sel_col:
        final_df = final_df[
            pd.Series(final_df["collection"]).isin(st.session_state.sel_col)
        ]
    if st.session_state.sel_size:
        final_df = final_df[pd.Series(final_df["size"]).isin(st.session_state.sel_size)]
    if st.session_state.sel_color:
        final_df = final_df[
            pd.Series(final_df["color"]).isin(st.session_state.sel_color)
        ]

    return final_df


def filter_column(df: pd.DataFrame, col: str, target: str):
    df_filtered = df[df[col].apply(lambda x: is_similar(x, target))]
    return df_filtered
