import streamlit as st
st.set_page_config(page_title = 'Mellanni Tools App', page_icon = 'media/logo.ico',layout="wide")

# import login
# st.session_state['login'] = login.login()
# st.write(st.session_state['login'])

# if st.session_state['login']:
#     st.write("logged in")

#### new google login ####
import login_google
st.session_state['login'] = login_google.login()

if st.session_state['login']:
    st.write("Logged in")

