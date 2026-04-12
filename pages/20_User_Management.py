import streamlit as st

from login import SUPER_ADMINS, require_login
from modules.supabase_client import get_supabase_client

st.set_page_config(
    page_title="User Management",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

require_login()

if st.user.email not in SUPER_ADMINS:
    st.stop()

supabase = get_supabase_client()

st.header("User Management")

ALL_ROLES = ["viewer", "sales", "admin"]


def load_users() -> list[dict]:
    result = supabase.table("app_users").select("*").order("email").execute()
    return result.data


def add_user(email: str, roles: list[str]) -> bool:
    try:
        supabase.table("app_users").insert({"email": email, "roles": roles}).execute()
        return True
    except Exception as e:
        st.error(f"Failed to add user: {e}")
        return False


def update_user(user_id: str, updates: dict):
    supabase.table("app_users").update(updates).eq("id", user_id).execute()


def delete_user(user_id: str):
    supabase.table("app_users").delete().eq("id", user_id).execute()


# --- Add new user ---
with st.expander("Add new user", icon=":material/person_add:"):
    col_email, col_roles, col_btn = st.columns([3, 2, 1])
    new_email = col_email.text_input("Email", placeholder="name@mellanni.com")
    new_roles = col_roles.multiselect("Roles", ALL_ROLES, default=["viewer"])
    col_btn.write("")
    col_btn.write("")
    if col_btn.button("Add", type="primary", use_container_width=True):
        if new_email and "@" in new_email:
            if not new_roles:
                st.warning("Select at least one role.")
            elif add_user(new_email.strip().lower(), new_roles):
                st.success(f"Added {new_email}")
                st.rerun()
        else:
            st.warning("Enter a valid email address.")

st.divider()

# --- Search / filter ---
col_search, col_role_filter = st.columns([3, 1])
search = col_search.text_input(
    "Search users", placeholder="Type to filter by email...", label_visibility="collapsed"
)
role_filter = col_role_filter.selectbox(
    "Filter by role", ["All"] + ALL_ROLES, label_visibility="collapsed"
)

# --- Load and filter users ---
users = load_users()

if search:
    users = [u for u in users if search.lower() in u["email"].lower()]
if role_filter != "All":
    users = [u for u in users if role_filter in u.get("roles", [])]

# Summary
active_count = sum(1 for u in users if u["is_active"])
st.caption(f"{len(users)} users shown, {active_count} active")

if not users:
    st.info("No users match the filter.")
    st.stop()

# --- Column headers ---
h_email, h_roles, h_active, h_delete = st.columns([4, 3, 1, 1])
h_email.markdown("**Email**")
h_roles.markdown("**Roles**")
h_active.markdown("**Active**")
h_delete.markdown("")

# --- User rows ---
for user in users:
    uid = user["id"]
    email = user["email"]
    is_super = email in SUPER_ADMINS
    user_roles = user.get("roles", ["viewer"])

    col_email, col_roles, col_active, col_delete = st.columns([4, 3, 1, 1])

    col_email.text(email)

    new_roles = col_roles.multiselect(
        "Roles",
        ALL_ROLES,
        default=user_roles,
        key=f"roles_{uid}",
        label_visibility="collapsed",
        disabled=is_super,
    )
    if sorted(new_roles) != sorted(user_roles) and not is_super:
        if new_roles:
            update_user(uid, {"roles": new_roles})
            st.rerun()
        else:
            st.toast("Users must have at least one role.")

    is_active = user["is_active"]
    new_active = col_active.toggle(
        "Active",
        value=is_active,
        key=f"active_{uid}",
        label_visibility="collapsed",
        disabled=is_super,
    )
    if new_active != is_active and not is_super:
        update_user(uid, {"is_active": new_active})
        st.rerun()

    if is_super:
        col_delete.write("")
    else:
        if col_delete.button(
            ":material/delete:",
            key=f"del_{uid}",
            use_container_width=True,
        ):
            delete_user(uid)
            st.rerun()
