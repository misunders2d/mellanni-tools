import streamlit as st
from login import require_login

st.set_page_config(
    page_title="Mellanni Tools App", page_icon="media/logo.ico", layout="wide"
)

from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.genai import types

from agents.agent import create_root_agent

from modules.read_file import read_file
from modules.telegram_notifier import send_telegram_message

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
# import traceback

load_dotenv()

APP_NAME = "mellanni_amz_agent"
show_tool_calls = False

require_login()

if "email" in st.user and isinstance(st.user.email, str):
    user_id = st.user.email
else:
    user_id = "unknown_user"
user_name = st.user.name if "name" in st.user else "Unknown User"
if "picture" in st.user and isinstance(st.user.picture, str):
    user_picture = st.user.picture
else:
    user_picture = "media/user_avatar.jpg"

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] == "thought":
        icon = "🧠"
        if message.get("type") == "tool_call":
            icon = "🔧"
        elif message.get("type") == "tool_response":
            icon = "📥"

        with st.expander(message["label"], icon=icon):
            if message.get("type") == "tool_response":
                st.json(message["content"])
            else:
                st.info(message["content"])
    else:
        with st.chat_message(
            message["role"],
            avatar=(
                user_picture if message["role"] == "user" else "media/jeff_avatar.jpeg"
            ),
        ):
            st.markdown(message["content"])


new_msg = ""


async def run_agent(user_input: str, session_id: str, user_id: str):
    global new_msg

    if "session_service" not in st.session_state:
        st.session_state["session_service"] = InMemorySessionService()
        await st.session_state["session_service"].create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
    else:
        await st.session_state["session_service"].get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
    session_service = st.session_state["session_service"]
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        agent=create_root_agent(),
        app_name=APP_NAME,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=user_input)]),
    ):
        if not event.content:
            continue
        if not event.content.parts:
            continue
        # An event can have multiple parts, iterate through them
        for part in event.content.parts:
            # Case 1: It's a "thought" from the planner
            if part.thought:
                thought_data = {
                    "role": "thought",
                    "type": "thought",
                    "label": "Thought",
                    "content": part.text,
                }
                st.session_state.messages.append(thought_data)
                with st.expander(thought_data["label"], icon="🧠"):
                    st.info(thought_data["content"])

            # Case 2: It's a tool call
            elif part.function_call and show_tool_calls:
                fc = part.function_call
                thought_data = {
                    "role": "thought",
                    "type": "tool_call",
                    "label": f"Tool Call: `{fc.name}`",
                    "content": f"Arguments: `{fc.args}`",
                }
                st.session_state.messages.append(thought_data)
                with st.expander(thought_data["label"], icon="🔧"):
                    st.info(thought_data["content"])

            # Case 3: It's a tool response
            elif part.function_response and show_tool_calls:
                fr = part.function_response
                thought_data = {
                    "role": "thought",
                    "type": "tool_response",
                    "label": f"Tool Response: `{fr.name}`",
                    "content": fr.response,
                }
                st.session_state.messages.append(thought_data)
                with st.expander(thought_data["label"], icon="📥"):
                    st.json(thought_data["content"])

            # Case 4: It's regular text for the final reply
            elif part.text:
                new_msg += part.text
                yield part.text

        # Handle errors at the event level
        if event.error_code:
            st.error(f"Sorry, the following error happened:\n{event.error_code}")


if prompt := st.chat_input(
    "Ask me what I can do ;)", accept_file=True, file_type=[".csv"]
):
    prompt_text = prompt.text
    prompt_files = prompt.files
    if prompt_files:
        for file in prompt_files:
            if file.type == "text/csv":
                df = read_file(file)
                prompt_text += f"\n\nHere is the file data:\n{df}"
            else:
                st.write(
                    f"Unsupported file type: {file.type}. Please upload a CSV file."
                )
                continue
    st.chat_message("user", avatar=user_picture).markdown(prompt.text)
    st.session_state.messages.append({"role": "user", "content": prompt.text})

    with st.chat_message("Jeff", avatar="media/jeff_avatar.jpeg"):
        try:
            st.write_stream(
                run_agent(
                    user_input=prompt_text,
                    session_id=f"{user_id}_session",
                    user_id=user_id,
                )
            )
        except Exception as e:
            error_message = f"Sorry, an error occurred, please try later:\n{e}"
            send_telegram_message(error_message)
            st.write(error_message)
            # st.write(traceback.format_exc())
    st.session_state.messages.append({"role": "assistant", "content": new_msg})
