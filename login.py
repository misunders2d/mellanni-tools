import streamlit as st

PREAUTHORIZED_EMAILS = st.secrets["preauthorized_emails"]


def login_screen():
    st.header("This app requires authorization.")
    st.subheader("Please log in.")
    st.button(
        "Log in with Google",
        on_click=st.login,
        use_container_width=True,
        type="primary",
    )


def require_login():
    """
    Checks if the user is logged in and authorized.
    If not, it stops the script execution.
    If yes, it displays the user info in the sidebar.
    """
    if not st.user.is_logged_in:
        login_screen()
        st.stop()
    elif st.user.email in PREAUTHORIZED_EMAILS:
        with st.sidebar:
            if "picture" in st.user and isinstance(st.user.picture, str):
                user_picture = st.user.picture
            else:
                user_picture = "media/user_avatar.jpg"
            st.image(user_picture, width=50)
            if "name" in st.user and isinstance(st.user.name, str):
                user_name = st.user.name
            else:
                user_name = "Unknown User"
            st.subheader(user_name)
            st.button("Log out", on_click=st.logout)
    else:
        st.write("You are not authorized to use this app")
        with st.sidebar:
            st.header(st.user.email)
            st.button("Log out", on_click=st.logout)
        st.stop()
