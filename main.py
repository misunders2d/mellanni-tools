import streamlit as st
import json
import os

if "VERTEXAI_CREDS" in st.secrets:
    try:
        creds_json = st.secrets["VERTEXAI_CREDS"]
        key_dict = json.loads(creds_json)

        temp_key_path = "vertex_ai_key.json"
        with open(temp_key_path, "w") as f:
            json.dump(key_dict, f)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_path

    except json.JSONDecodeError:
        st.stop()
    except Exception as e:
        st.stop()
else:
    st.write('creds NOT found')
    pass

PROJECT_ID = "creatives-agent"
REGION = "us-central1"

# aiplatform.init(project=PROJECT_ID, location=REGION)

st.title("Vertex AI Image Generation App")
st.write(f"Using Project: **{PROJECT_ID}** in Region: **{REGION}**")