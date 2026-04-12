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


# --- Data helpers ---
def load_roles() -> list[str]:
    result = supabase.table("app_roles").select("name").order("name").execute()
    return [r["name"] for r in result.data]


def load_roles_with_descriptions() -> list[dict]:
    result = supabase.table("app_roles").select("*").order("name").execute()
    return result.data


def add_role(name: str, description: str) -> bool:
    try:
        supabase.table("app_roles").insert(
            {"name": name, "description": description}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Failed to add role: {e}")
        return False


def delete_role(name: str):
    # Remove this role from all users who have it
    users = supabase.table("app_users").select("id, roles").execute().data
    for user in users:
        if name in user.get("roles", []):
            new_roles = [r for r in user["roles"] if r != name]
            if not new_roles:
                new_roles = ["viewer"]
            supabase.table("app_users").update({"roles": new_roles}).eq(
                "id", user["id"]
            ).execute()
    supabase.table("app_roles").delete().eq("name", name).execute()


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


# --- Load roles ---
ALL_ROLES = load_roles()

# --- Tabs ---
users_tab, roles_tab, agents_tab, otps_tab = st.tabs(
    ["Users", "Roles", "Remote Agents", "OTPs"]
)

# ==================== USERS TAB ====================
with users_tab:
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

    # --- Load users first (needed for search options) ---
    users = load_users()
    all_emails = [u["email"] for u in users]

    # --- Search / filter ---
    col_search, col_role_filter = st.columns([3, 1])

    # search = col_search.selectbox(
    #     label="Search users",
    #     options=all_emails,
    #     placeholder="Type to filter by email...",
    #     label_visibility="collapsed",
    # )

    search = col_search.text_input(
        label="Search users",
        placeholder="Type to filter by email...",
        label_visibility="collapsed",
    )

    role_filter = col_role_filter.selectbox(
        "Filter by role", ["All"] + ALL_ROLES, label_visibility="collapsed"
    )

    if search:
        users = [u for u in users if search.lower() in u["email"].lower()]
    if role_filter != "All":
        users = [u for u in users if role_filter in u.get("roles", [])]

    active_count = sum(1 for u in users if u["is_active"])
    st.caption(f"{len(users)} users shown, {active_count} active")

    if not users:
        st.info("No users match the filter.")
    else:
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

# ==================== ROLES TAB ====================
with roles_tab:
    PROTECTED_ROLES = {"viewer", "sales", "admin"}

    # --- Add new role ---
    with st.expander("Add new role", icon=":material/add_circle:"):
        col_name, col_desc, col_btn = st.columns([2, 3, 1])
        role_name = col_name.text_input("Role name", placeholder="e.g. photoshop")
        role_desc = col_desc.text_input(
            "Description", placeholder="e.g. Access to AI Photoshop tool"
        )
        col_btn.write("")
        col_btn.write("")
        if col_btn.button(
            "Create", type="primary", use_container_width=True, key="create_role"
        ):
            if role_name:
                clean_name = role_name.strip().lower().replace(" ", "_")
                if clean_name in ALL_ROLES:
                    st.warning(f"Role '{clean_name}' already exists.")
                elif add_role(clean_name, role_desc.strip()):
                    st.success(f"Created role '{clean_name}'")
                    st.rerun()
            else:
                st.warning("Enter a role name.")

    st.divider()

    # --- Existing roles ---
    roles = load_roles_with_descriptions()
    all_users = load_users()

    # Column headers
    h_name, h_desc, h_users, h_action = st.columns([2, 4, 1, 1])
    h_name.markdown("**Role**")
    h_desc.markdown("**Description**")
    h_users.markdown("**Users**")
    h_action.markdown("")

    for role in roles:
        name = role["name"]
        is_protected = name in PROTECTED_ROLES

        col_name, col_desc, col_users, col_action = st.columns([2, 4, 1, 1])

        col_name.markdown(f"**{name}**")

        # Editable description
        new_desc = col_desc.text_input(
            "Description",
            value=role.get("description") or "",
            key=f"desc_{name}",
            label_visibility="collapsed",
        )
        if new_desc != (role.get("description") or ""):
            supabase.table("app_roles").update({"description": new_desc}).eq(
                "name", name
            ).execute()

        user_count = sum(1 for u in all_users if name in u.get("roles", []))
        col_users.caption(f"{user_count} users")

        if is_protected:
            col_action.markdown(
                ":material/lock:", help="Built-in role, cannot be deleted"
            )
        else:
            if col_action.button(
                ":material/delete:",
                key=f"del_role_{name}",
                use_container_width=True,
            ):
                delete_role(name)
                st.success(f"Deleted role '{name}' and removed it from all users")
                st.rerun()

# ==================== REMOTE AGENTS TAB ====================
with agents_tab:
    import asyncio
    from modules.a2a_client import discover_agent

    def load_remote_agents() -> list[dict]:
        result = supabase.table("remote_agents").select("*").order("name").execute()
        return result.data

    def add_remote_agent(name: str, url: str, description: str) -> bool:
        try:
            supabase.table("remote_agents").insert(
                {"name": name, "url": url.rstrip("/"), "description": description}
            ).execute()
            return True
        except Exception as e:
            st.error(f"Failed to add agent: {e}")
            return False

    # --- Add new agent ---
    with st.expander("Add remote agent", icon=":material/smart_toy:"):
        col_name, col_url, col_desc = st.columns([2, 3, 3])
        agent_name = col_name.text_input("Name", placeholder="e.g. ori")
        agent_url = col_url.text_input("URL", placeholder="https://your-agent.example.com")
        agent_desc = col_desc.text_input(
            "Description", placeholder="e.g. Primary Ori agent"
        )
        if st.button("Add Agent", type="primary", key="add_agent"):
            if agent_name and agent_url:
                if add_remote_agent(
                    agent_name.strip().lower(), agent_url.strip(), agent_desc.strip()
                ):
                    st.success(f"Added agent '{agent_name}'")
                    st.rerun()
            else:
                st.warning("Name and URL are required.")

    st.divider()

    # --- Existing agents ---
    agents = load_remote_agents()

    if not agents:
        st.info("No remote agents configured.")
    else:
        for agent in agents:
            aid = agent["id"]
            col_name, col_url, col_active, col_actions = st.columns([2, 4, 1, 2])

            col_name.markdown(f"**{agent['name']}**")
            if agent.get("description"):
                col_name.caption(agent["description"])

            # Editable URL
            new_url = col_url.text_input(
                "URL",
                value=agent["url"],
                key=f"url_{aid}",
                label_visibility="collapsed",
            )
            if new_url != agent["url"]:
                supabase.table("remote_agents").update(
                    {"url": new_url.rstrip("/")}
                ).eq("id", aid).execute()
                # Clear cached remote agent
                if "remote_agent" in st.session_state:
                    del st.session_state["remote_agent"]
                st.rerun()

            is_active = agent["is_active"]
            new_active = col_active.toggle(
                "Active",
                value=is_active,
                key=f"agent_active_{aid}",
                label_visibility="collapsed",
            )
            if new_active != is_active:
                supabase.table("remote_agents").update(
                    {"is_active": new_active}
                ).eq("id", aid).execute()
                if "remote_agent" in st.session_state:
                    del st.session_state["remote_agent"]
                st.rerun()

            # Test connection button
            btn_col, del_col = col_actions.columns(2)
            if btn_col.button(":material/wifi:", key=f"test_{aid}", help="Test connection"):
                with st.spinner("Discovering agent..."):
                    card = asyncio.run(discover_agent(agent["url"]))
                    if card:
                        st.success(
                            f"Connected to **{card.get('name', 'Unknown')}** "
                            f"(v{card.get('version', '?')})"
                        )
                    else:
                        st.error(f"Could not reach agent at {agent['url']}")

            if del_col.button(":material/delete:", key=f"del_agent_{aid}"):
                supabase.table("remote_agents").delete().eq("id", aid).execute()
                if "remote_agent" in st.session_state:
                    del st.session_state["remote_agent"]
                st.rerun()

# ==================== OTPs TAB ====================
with otps_tab:
    from modules.crypto import encrypt

    st.caption(
        "Manage TOTP (2FA) secrets. Secrets are encrypted before storage. "
        "Users will only see OTPs where their email is in the allowed list."
    )

    def load_otps() -> list[dict]:
        result = supabase.table("otps").select("*").order("label").execute()
        return result.data

    # Load all users for the multiselect (ensures consistent email options)
    all_user_emails = sorted(u["email"] for u in load_users())

    # --- Add new OTP ---
    with st.expander("Add new OTP", icon=":material/add_circle:"):
        col_label, col_secret = st.columns([2, 3])
        new_label = col_label.text_input(
            "Label", placeholder="e.g. US: Vitalii", key="new_otp_label"
        )
        new_secret = col_secret.text_input(
            "TOTP secret (base32)",
            placeholder="ABCD EFGH IJKL MNOP",
            key="new_otp_secret",
            type="password",
        )
        new_allowed = st.multiselect(
            "Allowed users",
            options=all_user_emails,
            key="new_otp_emails",
        )
        if st.button("Add OTP", type="primary", key="add_otp_btn"):
            if not new_label or not new_secret:
                st.warning("Label and secret are required.")
            elif not new_allowed:
                st.warning("Select at least one user.")
            else:
                try:
                    supabase.table("otps").insert({
                        "label": new_label.strip(),
                        "encrypted_secret": encrypt(new_secret.strip()),
                        "allowed_emails": new_allowed,
                    }).execute()
                    st.success(f"Added OTP '{new_label}'")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add OTP: {e}")

    st.divider()

    # --- Search ---
    search = st.text_input(
        "Search OTPs",
        placeholder="Type to filter by label...",
        label_visibility="collapsed",
        key="otp_search",
    )

    otps = load_otps()
    if search:
        otps = [o for o in otps if search.lower() in o["label"].lower()]

    st.caption(f"{len(otps)} OTPs")

    if not otps:
        st.info("No OTPs match the filter.")
    else:
        # Column headers
        h_label, h_emails, h_actions = st.columns([2, 4, 1])
        h_label.markdown("**Label**")
        h_emails.markdown("**Allowed users**")
        h_actions.markdown("")

        for otp_row in otps:
            oid = otp_row["id"]
            col_label, col_emails, col_actions = st.columns([2, 4, 1])

            current_label = otp_row["label"]
            new_label = col_label.text_input(
                "Label",
                value=current_label,
                key=f"otp_label_{oid}",
                label_visibility="collapsed",
            )
            if new_label.strip() and new_label.strip() != current_label:
                try:
                    supabase.table("otps").update(
                        {"label": new_label.strip()}
                    ).eq("id", oid).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to rename OTP: {e}")

            current_emails = otp_row.get("allowed_emails") or []
            # Include orphan emails (allowed but no longer in app_users) so they're visible
            options = sorted(set(all_user_emails) | set(current_emails))

            new_emails = col_emails.multiselect(
                "Allowed users",
                options=options,
                default=current_emails,
                key=f"otp_emails_{oid}",
                label_visibility="collapsed",
            )
            if sorted(new_emails) != sorted(current_emails):
                supabase.table("otps").update(
                    {"allowed_emails": new_emails}
                ).eq("id", oid).execute()
                st.rerun()

            if col_actions.button(":material/delete:", key=f"del_otp_{oid}"):
                supabase.table("otps").delete().eq("id", oid).execute()
                st.rerun()
