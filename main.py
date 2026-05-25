import asyncio
import logging
import uuid
from io import StringIO

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from login import require_login
import time

from modules.a2a_client import get_remote_agent, get_task, send_message, parse_response
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
PREFERRED_A2A_AGENT = "you"
remote_agent = get_remote_agent(preferred_name=PREFERRED_A2A_AGENT)
if not remote_agent:
    st.error("No remote agent configured. Ask an admin to set one up in User Management.")
    st.stop()

agent_url = remote_agent["url"]
agent_name = remote_agent.get("name") or PREFERRED_A2A_AGENT
a2a_secrets = st.secrets.get("a2a", {})
a2a_api_key = a2a_secrets.get("api_key")
a2a_app_token = (
    a2a_secrets.get("app_token")
    or a2a_secrets.get("bearer_token")
    or a2a_secrets.get("token")
)
a2a_client_id = a2a_secrets.get("client_id", "mellanni-tools-streamlit")
a2a_agent_id = a2a_secrets.get("agent_id", a2a_client_id)
a2a_key_id = a2a_secrets.get("key_id", "mellanni-website-v1")
a2a_private_key_pem = a2a_secrets.get("private_key_pem")
a2a_scoped_token = a2a_secrets.get("scoped_token") or a2a_app_token
# Signature principal is the registered client identity, not the end user.
# End-user id travels in message metadata (caller_id/user_id below).
a2a_principal = a2a_secrets.get("principal", "website:mellanni")

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
if "a2a_pending_task_id" not in st.session_state:
    st.session_state.a2a_pending_task_id = None


def _render_table(csv_text: str):
    df = pd.read_csv(StringIO(csv_text))
    st.dataframe(df, use_container_width=True, hide_index=True)
    return df


def _render_file_artifact(file_info: dict, key_prefix: str):
    data = file_info.get("data", b"")
    mime = file_info.get("mime_type") or "application/octet-stream"
    name = file_info.get("name") or "artifact"

    if isinstance(data, str):
        raw_data = data.encode("utf-8")
    else:
        raw_data = data

    if mime.startswith("image/"):
        st.image(raw_data, caption=name)
    elif "html" in mime:
        html = raw_data.decode("utf-8", errors="replace")
        components.html(html, height=600)
    elif "csv" in mime or name.endswith(".csv"):
        csv_text = raw_data.decode("utf-8", errors="replace")
        _render_table(csv_text)
    elif mime.startswith("text/") or name.endswith((".txt", ".md", ".json")):
        st.code(raw_data.decode("utf-8", errors="replace"))

    st.download_button(
        f"Download {name}",
        data=raw_data,
        file_name=name,
        mime=mime,
        key=f"{key_prefix}_{name}_{len(raw_data)}",
    )


def _render_artifact_message(message: dict, key_prefix: str):
    artifact_type = message.get("type")
    if artifact_type == "image":
        st.image(message["content"])
    elif artifact_type == "plot":
        components.html(message["content"], height=600)
    elif artifact_type == "table":
        st.dataframe(message["content"], use_container_width=True, hide_index=True)
    elif artifact_type == "file":
        _render_file_artifact(message["content"], key_prefix)


# --- Render chat history ---
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "artifact":
        _render_artifact_message(message, f"history_{idx}")
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


def _agent_needs_legacy_caller_tag(name: str) -> bool:
    """Older Ori server used a text tag; new A2A agents read metadata."""
    return name.strip().lower() in {"ori", "jeff"}


# --- Chat input ---
if prompt := st.chat_input("Ask me what I can do ;)"):
    st.chat_message("user", avatar=user_picture).markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message(agent_name, avatar="media/jeff_avatar.jpeg"):
        with st.spinner("Thinking..."):
            try:
                # New A2A agents receive caller identity in message metadata.
                # Keep Ori-compatible tag only for legacy agents that strip it server-side.
                a2a_metadata = {
                    "agentId": a2a_agent_id,
                    "toAgent": "pi-remote-hub",
                    "caller_id": user_id,
                    "user_id": user_id,
                    "source": "mellanni-tools-streamlit",
                }
                if _agent_needs_legacy_caller_tag(agent_name):
                    a2a_message = f"[__caller_id:{user_id}__]{prompt}"
                else:
                    a2a_message = prompt
                logger.info(
                    "A2A outbound: agent=%s, context_id=%s, message=%s",
                    agent_name,
                    st.session_state.a2a_context_id,
                    a2a_message[:100],
                )

                rpc_response = asyncio.run(
                    send_message(
                        url=agent_url,
                        api_key=a2a_api_key,
                        app_token=a2a_app_token,
                        client_id=a2a_client_id,
                        message=a2a_message,
                        context_id=st.session_state.a2a_context_id,
                        task_id=st.session_state.a2a_pending_task_id,
                        metadata=a2a_metadata,
                        agent_id=a2a_agent_id,
                        principal=a2a_principal,
                        key_id=a2a_key_id,
                        private_key_pem=a2a_private_key_pem,
                        scoped_token=a2a_scoped_token,
                    )
                )

                parsed = parse_response(
                    rpc_response,
                    api_key=a2a_api_key,
                    app_token=a2a_app_token,
                    client_id=a2a_client_id,
                    base_url=agent_url,
                    agent_id=a2a_agent_id,
                    principal=user_id,
                    key_id=a2a_key_id,
                    private_key_pem=a2a_private_key_pem,
                    scoped_token=a2a_scoped_token,
                )

                logger.info(
                    "A2A parsed: state=%s task_id=%s",
                    parsed.get("state"), parsed.get("task_id"),
                )

                # Hub returns submitted/working while the manager agent processes.
                # Poll tasks/get until terminal state or timeout.
                pending_states = {"submitted", "working"}
                poll_deadline = time.time() + 120
                while parsed.get("state") in pending_states and parsed.get("task_id"):
                    if time.time() >= poll_deadline:
                        logger.warning(
                            "A2A poll timeout on task %s state=%s",
                            parsed.get("task_id"), parsed.get("state"),
                        )
                        break
                    time.sleep(2.0)
                    rpc_response = asyncio.run(
                        get_task(
                            url=agent_url,
                            task_id=parsed["task_id"],
                            api_key=a2a_api_key,
                            app_token=a2a_app_token,
                            client_id=a2a_client_id,
                            agent_id=a2a_agent_id,
                            principal=a2a_principal,
                            key_id=a2a_key_id,
                            private_key_pem=a2a_private_key_pem,
                            scoped_token=a2a_scoped_token,
                        )
                    )
                    parsed = parse_response(
                        rpc_response,
                        api_key=a2a_api_key,
                        app_token=a2a_app_token,
                        client_id=a2a_client_id,
                        base_url=agent_url,
                        agent_id=a2a_agent_id,
                        principal=a2a_principal,
                        key_id=a2a_key_id,
                        private_key_pem=a2a_private_key_pem,
                        scoped_token=a2a_scoped_token,
                    )
                    logger.info("A2A poll: state=%s", parsed.get("state"))

                if parsed["error"]:
                    st.error(f"Agent error: {parsed['error']}")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": f"Error: {parsed['error']}"}
                    )
                elif parsed["state"] in {"failed", "canceled"} and not parsed.get("text"):
                    msg = f"Task {parsed['state']} with no payload (task_id={parsed.get('task_id')})"
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})
                else:
                    # Display text response
                    if parsed["text"]:
                        st.markdown(parsed["text"])
                        st.session_state.messages.append(
                            {"role": "assistant", "content": parsed["text"]}
                        )

                    if parsed.get("files"):
                        for idx, file_info in enumerate(parsed["files"]):
                            _render_file_artifact(file_info, f"live_{idx}")
                            st.session_state.messages.append(
                                {
                                    "role": "artifact",
                                    "type": "file",
                                    "content": file_info,
                                }
                            )
                    else:
                        # Backward-compatible handling for parser outputs that
                        # predate the generic file bucket.
                        for img_data in parsed["images"]:
                            st.image(img_data)
                            st.session_state.messages.append(
                                {"role": "artifact", "type": "image", "content": img_data}
                            )

                        for html_content in parsed["html"]:
                            components.html(html_content, height=600)
                            st.session_state.messages.append(
                                {
                                    "role": "artifact",
                                    "type": "plot",
                                    "content": html_content,
                                }
                            )

                        for csv_text in parsed["tables"]:
                            try:
                                df = _render_table(csv_text)
                                st.session_state.messages.append(
                                    {"role": "artifact", "type": "table", "content": df}
                                )
                            except Exception:
                                st.text(csv_text)

                    # Handle input_required state (A2A spec spells it with hyphen)
                    if parsed["state"] in {"input_required", "input-required"}:
                        st.session_state.a2a_pending_task_id = parsed.get("task_id")
                        st.info("The agent needs more information. Please respond above.")
                    else:
                        st.session_state.a2a_pending_task_id = None

            except Exception as e:
                error_message = f"Failed to reach the remote agent: {e}"
                logger.error(error_message)
                send_telegram_message(error_message)
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )
