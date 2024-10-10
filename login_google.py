import streamlit as st
from streamlit_oauth import OAuth2Component
import os, time
import base64
import json

# import logging
# logging.basicConfig(level=logging.INFO)

# st.title("Google OIDC Example")
# st.write("This example shows how to use the raw OAuth2 component to authenticate with a Google OAuth2 and get email from id_token.")

# create an OAuth2Component instance
CLIENT_ID = os.environ.get("GCLIENT_ID")
CLIENT_SECRET = os.environ.get("GCLIENT_SECRET")
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
PREAUTHORIZED_EMAILS = st.secrets['preauthorized_emails']['emails']

def logout():
    if 'auth' in st.session_state:
        del st.session_state["auth"]
    if 'token' in st.session_state:
        del st.session_state["token"]

def login():
    if "auth" not in st.session_state:
        # create a button to start the OAuth2 flow
        oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_ENDPOINT, TOKEN_ENDPOINT, TOKEN_ENDPOINT, REVOKE_ENDPOINT)
        result = oauth2.authorize_button(
            name="Continue with Google",
            icon="https://www.google.com.tw/favicon.ico",
            redirect_uri="https://mellanni-tools.streamlit.app/",
            scope="openid email profile",
            key="google",
            extras_params={"prompt": "consent", "access_type": "offline"},
            use_container_width=False 
        )

        if result:
            # st.write(result)
            # decode the id_token jwt and get the user's email address
            id_token = result["token"]["id_token"]
            # verify the signature is an optional step for security
            payload = id_token.split(".")[1]
            # add padding to the payload if needed
            payload += "=" * (-len(payload) % 4)
            payload = json.loads(base64.b64decode(payload))
            email = payload["email"]
            st.session_state["auth"] = email
            st.session_state["token"] = result["token"]
            time.sleep(0.5)
            st.rerun()
    else:
        st.write("You are logged in!")
        st.write('Your email:',st.session_state["auth"])
        if st.session_state['auth'] in PREAUTHORIZED_EMAILS:
            return True, st.session_state["auth"]
        # st.write(st.session_state["token"])
        # st.button("Logout")
    st.write("You are not allowed to access this page")
    if st.button("Logout"):
        logout()
    return False, 'Access denied'