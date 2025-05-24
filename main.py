import streamlit as st
from login import login_st
st.set_page_config(page_title = 'Mellanni Tools App', page_icon = 'media/logo.ico',layout="wide")


if login_st():
    st.write(f'logged in as {st.user.email}')
