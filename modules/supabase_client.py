"""Supabase client helper for the mellanni-tools app."""

import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase_client():
    """Return a cached Supabase client using secrets from .streamlit/secrets.toml."""
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"],
    )
