import json
import os

import streamlit as st

from modules.gcloud_modules import pull_dictionary
from modules.supabase_client import get_supabase_client

SUPER_ADMINS = ["2djohar@gmail.com", "sergey@mellanni.com"]

try:
    bigquery_service_account_info = st.secrets.get("gcp_service_account", "")
except Exception as e:
    print(e)
    bigquery_service_account_info = json.loads(
        os.environ.get("gcp_service_account", "")
    )

pull_dictionary()


def get_current_user() -> dict | None:
    """Look up the logged-in user in Supabase, cached in session state."""
    if "current_user" in st.session_state:
        return st.session_state["current_user"]

    supabase = get_supabase_client()
    result = (
        supabase.table("app_users")
        .select("*")
        .eq("email", st.user.email)
        .eq("is_active", True)
        .execute()
    )

    if result.data:
        st.session_state["current_user"] = result.data[0]
        return result.data[0]

    st.session_state["current_user"] = None
    return None


def login_screen():
    st.header("This app requires authorization.")
    st.subheader("Please log in.")
    st.button(
        "Log in with Google",
        on_click=st.login,
        use_container_width=True,
        type="primary",
    )


def require_login():
    """
    Checks if the user is logged in and authorized via Supabase.
    """
    if not st.user.is_logged_in:
        login_screen()
        st.stop()

    # Hide admin page from sidebar for non-super-admins
    if st.user.email not in SUPER_ADMINS:
        st.markdown(
            '<style>[data-testid="stSidebarNav"] li:has(a[href*="User_Management"]) {display: none;}</style>',
            unsafe_allow_html=True,
        )

    user = get_current_user()
    if user is not None:
        with st.sidebar:
            user_picture = (
                user.get("picture_url")
                or (st.user.picture if "picture" in st.user and isinstance(st.user.picture, str) else None)
                or "media/user_avatar.jpg"
            )
            st.image(user_picture, width=50)
            user_name = user.get("name") or st.user.get("name", "Unknown User")
            st.subheader(user_name)
            st.button("Log out", on_click=st.logout)
        return

    st.write("You are not authorized to use this app")
    with st.sidebar:
        st.header(st.user.email)
        st.button("Log out", on_click=st.logout)
    st.stop()


def require_role(*roles: str):
    """Check if the current user has any of the specified roles."""
    user = get_current_user()
    if user is not None:
        user_roles = user.get("roles", [])
        if any(r in user_roles for r in roles):
            return

    st.toast(
        f"User {st.user.email} does not have access to this section. "
        "Contact Sergey for details."
    )
    st.stop()
