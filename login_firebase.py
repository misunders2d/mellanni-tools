import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import json
import requests

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(r"C:\temp\pics\mellanni-login.json")
    firebase_admin.initialize_app(cred)

# Streamlit app
def app():
    st.title("Streamlit App with Google Login")
    
    # Session state
    if 'user' not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        # Google Sign-In button
        google_signin_url = "https://accounts.google.com/o/oauth2/v2/auth?" + \
                            "client_id=299757840028-hifafkuj5mhui2e8b9a932scq0c3go59.apps.googleusercontent.com&" + \
                            "redirect_uri=http://localhost:8501/&" + \
                            "response_type=token&" + \
                            "scope=email%20profile"
        
        st.markdown(f'<a href="{google_signin_url}" target="_self"><button>Login with Google</button></a>', unsafe_allow_html=True)

        # Check for authentication response
        if 'id_token' in st.experimental_get_query_params():
            id_token = st.experimental_get_query_params()['id_token'][0]
            
            try:
                # Verify the ID token
                decoded_token = auth.verify_id_token(id_token)
                st.session_state.user = decoded_token
                st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {e}")
    else:
        st.write(f"Welcome, {st.session_state.user['name']}!")
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

if __name__ == "__main__":
    app()