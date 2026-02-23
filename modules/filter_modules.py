import pandas as pd
import streamlit as st

from modules import gcloud_modules as gc


async def filter_dictionary(col=None):
    """
    Filters the dictionary based on selected collection, size or color
    """
    target = col if col else st

    def clear_selection():
        for key in ["sel_col", "sel_size", "sel_color"]:
            st.session_state[key] = []

    if "dictionary" not in st.session_state:
        st.session_state.dictionary = await gc.pull_dictionary()
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
    with target.popover(
        label="Select products", icon=":material/shelves:", width="stretch"
    ):
        st.multiselect(
            "Collections",
            options=opt_col,
            key="sel_col",
            placeholder="Select collection(s)",
        )
        st.multiselect(
            "Sizes", options=opt_size, key="sel_size", placeholder="Select size(s)"
        )
        st.multiselect(
            "Colors", options=opt_color, key="sel_color", placeholder="Select color(s)"
        )
        st.button("Clear selection", on_click=clear_selection)

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
