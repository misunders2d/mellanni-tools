import asyncio
import logging
import uuid
from io import StringIO

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from login import require_login
from modules.a2a_client import get_remote_agent, send_message, parse_response
from modules.telegram_notifier import send_telegram_message

st.set_page_config(
    page_title="Mellanni Tools App", page_icon="media/logo.ico", layout="wide"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

show_tool_calls = False
thought_icon = ":material/lightbulb_2:"

require_login()

# --- Remote agent config ---
remote_agent = get_remote_agent()
if not remote_agent:
    st.error("No remote agent configured. Ask an admin to set one up in User Management.")
    st.stop()

agent_url = remote_agent["url"]
agent_name = remote_agent.get("name", "Ori")
a2a_api_key = st.secrets["a2a"]["api_key"]

# --- User info ---
if "email" in st.user and isinstance(st.user.email, str):
    user_id = st.user.email
else:
    user_id = "unknown_user"

if "picture" in st.user and isinstance(st.user.picture, str):
    user_picture = st.user.picture
else:
    user_picture = "media/user_avatar.jpg"

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
# Persistent context_id ties all messages to one session on the remote agent
if "a2a_context_id" not in st.session_state:
    # Use a clean context_id without special characters
    email_prefix = user_id.split("@")[0] if "@" in user_id else user_id
    st.session_state.a2a_context_id = f"st_{email_prefix}_{uuid.uuid4().hex[:8]}"

# --- Render chat history ---
for message in st.session_state.messages:
    if message["role"] == "artifact":
        if message.get("type") == "image":
            st.image(message["content"])
        elif message.get("type") == "plot":
            components.html(message["content"], height=600)
        elif message.get("type") == "table":
            st.dataframe(message["content"], use_container_width=True, hide_index=True)
    else:
        with st.chat_message(
            message["role"],
            avatar=(
                user_picture
                if message["role"] == "user"
                else "media/jeff_avatar.jpeg"
            ),
        ):
            st.markdown(message["content"])

# --- Chat input ---
if prompt := st.chat_input("Ask me what I can do ;)"):
    st.chat_message("user", avatar=user_picture).markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message(agent_name, avatar="media/jeff_avatar.jpeg"):
        with st.spinner("Thinking..."):
            try:
                # Inject caller ID tag so Ori sets the correct user_id in session state.
                # The tag is stripped by Ori's state_setter callback before the model sees it.
                a2a_message = f"[__caller_id:{user_id}__]{prompt}"
                logger.info(
                    "A2A outbound: context_id=%s, message=%s",
                    st.session_state.a2a_context_id,
                    a2a_message[:100],
                )

                rpc_response = asyncio.run(
                    send_message(
                        url=agent_url,
                        api_key=a2a_api_key,
                        message=a2a_message,
                        context_id=st.session_state.a2a_context_id,
                    )
                )

                parsed = parse_response(rpc_response)

                if parsed["error"]:
                    st.error(f"Agent error: {parsed['error']}")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": f"Error: {parsed['error']}"}
                    )
                else:
                    # Display text response
                    if parsed["text"]:
                        st.markdown(parsed["text"])
                        st.session_state.messages.append(
                            {"role": "assistant", "content": parsed["text"]}
                        )

                    # Display images
                    for img_data in parsed["images"]:
                        st.image(img_data)
                        st.session_state.messages.append(
                            {"role": "artifact", "type": "image", "content": img_data}
                        )

                    # Display HTML plots
                    for html_content in parsed["html"]:
                        components.html(html_content, height=600)
                        st.session_state.messages.append(
                            {"role": "artifact", "type": "plot", "content": html_content}
                        )

                    # Display CSV tables
                    for csv_text in parsed["tables"]:
                        try:
                            df = pd.read_csv(StringIO(csv_text))
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            st.session_state.messages.append(
                                {"role": "artifact", "type": "table", "content": df}
                            )
                        except Exception:
                            st.text(csv_text)

                    # Handle input_required state
                    if parsed["state"] == "input_required":
                        st.info("The agent needs more information. Please respond above.")

            except Exception as e:
                error_message = f"Failed to reach the remote agent: {e}"
                logger.error(error_message)
                send_telegram_message(error_message)
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )
