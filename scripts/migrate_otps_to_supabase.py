"""One-time migration: read OTPs from st.secrets, encrypt, insert to Supabase.

Run with: uv run streamlit run scripts/migrate_otps_to_supabase.py

Reads from st.secrets["otps"]["users"] (the existing JSON blob) and creates
one row per (label, allowed_emails) combination. Safe to re-run — skips
labels that already exist in Supabase.
"""

import json
import sys
from pathlib import Path

# Allow running from the project root or from scripts/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from modules.crypto import encrypt
from modules.supabase_client import get_supabase_client

st.set_page_config(page_title="OTP Migration", layout="centered")
st.header("Migrate OTPs from secrets.toml to Supabase")

st.warning(
    "This is a one-time migration. It reads from st.secrets['otps']['users'] "
    "and inserts encrypted rows into the 'otps' Supabase table."
)

if st.button("Run migration", type="primary"):
    supabase = get_supabase_client()
    raw = json.loads(st.secrets["otps"]["users"])

    # Flatten: iterate over every (label, secret) pair, merging allowed_emails
    # across entries that share the same label (e.g., the same account can be
    # listed in multiple entries with different email groups).
    combined: dict[str, dict] = {}
    for entry in raw:
        emails = entry.get("emails", [])
        data = entry.get("data", {})
        for label, secret in data.items():
            if label not in combined:
                combined[label] = {"secret": secret, "emails": set()}
            combined[label]["emails"].update(emails)

    # Load existing labels to avoid duplicates
    existing = supabase.table("otps").select("label").execute().data
    existing_labels = {row["label"] for row in existing}

    inserted = 0
    skipped = 0
    failed = 0

    progress = st.progress(0)
    status = st.empty()

    items = list(combined.items())
    for i, (label, info) in enumerate(items):
        if label in existing_labels:
            skipped += 1
            continue
        try:
            supabase.table("otps").insert({
                "label": label,
                "encrypted_secret": encrypt(info["secret"]),
                "allowed_emails": sorted(info["emails"]),
            }).execute()
            inserted += 1
        except Exception as e:
            failed += 1
            status.error(f"Failed to insert '{label}': {e}")
        progress.progress((i + 1) / len(items))

    st.success(
        f"Migration complete. Inserted: {inserted}, skipped (already existed): {skipped}, failed: {failed}"
    )
    st.caption(
        "You can now remove the [otps] section from .streamlit/secrets.toml "
        "once you've verified the OTPs work on the Tools page."
    )
