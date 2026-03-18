import json
import os
import tempfile

import streamlit as st

if "AMZ_CLIENT_ID" not in st.session_state:
    os.environ["AMZ_CLIENT_ID"] = st.secrets["AMZ_CLIENT_ID"]
    os.environ["AMZ_CLIENT_SECRET"] = st.secrets["AMZ_CLIENT_SECRET"]
    os.environ["AMZ_REFRESH_TOKEN_US"] = st.secrets["AMZ_REFRESH_TOKEN_US"]
    os.environ["AMZ_SELLER_ID"] = st.secrets["AMZ_SELLER_ID"]

    try:
        bigquery_service_account_info = st.secrets.get("gcp_service_account", "")
    except Exception as e:
        print(e)
        bigquery_service_account_info = json.loads(
            os.environ.get("gcp_service_account", "")
        )

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".json"
    ) as temp_key_file:
        json.dump(dict(bigquery_service_account_info), temp_key_file)
        temp_key_file_path = temp_key_file.name
    os.environ["gcp_service_account"] = temp_key_file_path
