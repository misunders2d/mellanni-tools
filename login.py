import streamlit as st
# import os
from dotenv import load_dotenv
# load_dotenv()

PREAUTHORIZED_EMAILS = st.secrets['preauthorized_emails']

def login_screen():
    st.header("This app requires authorization.")
    st.subheader("Please log in.")
    st.button("Log in with Google", on_click=st.login, use_container_width=True, type="primary")


def login_st():
    if not st.user.is_logged_in:
        login_screen()
    elif st.user.email in PREAUTHORIZED_EMAILS:
        with st.sidebar:
            st.image(st.user.get('picture','media/user_avatar.jpg'), width=50)
            st.subheader(st.user.name)
            st.button("Log out", on_click=st.logout)
        return True
    else:
        st.write('You are not authorized to use this app')
        with st.sidebar:
            st.header(st.user.email)
            st.button("Log out", on_click=st.logout)            
        return False