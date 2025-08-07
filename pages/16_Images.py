import streamlit as st

##################################### PAGE CONFIG #######################################
st.set_page_config(page_title = 'Mellanni knowledge base', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')

st.subheader('Mellanni Images management')

from login import login_st
if login_st():



    st.image("media/obsolete.jpg", width=400)
    st.markdown(
        """
        ### This page is has been moved to a new location.
        ### Please use this [Link](https://mellanni-images.streamlit.app/) instead.
        """
    )

