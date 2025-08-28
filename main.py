import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from io import StringIO

import asyncio

from login import require_login

st.set_page_config(
    page_title="Mellanni Tools App", page_icon="media/logo.ico", layout="wide"
)

from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.genai import types

from agents.agent import create_root_agent
from modules.telegram_notifier import send_telegram_message

import logging
import re
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

APP_NAME = "mellanni_amz_agent"
show_tool_calls = False
tool_call_icon = ":material/construction:"
tool_response_icon = ":material/quick_reference:"
thought_icon = ":material/lightbulb_2:"

require_login()

with st.sidebar:
    include_tool_calls = st.checkbox(
        "Include tool calls output?",
        value=show_tool_calls,
        help="Checking this box will include tool/function calls in the chat, used for debugging",
    )

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

if "artifact_service" not in st.session_state:
    st.session_state["artifact_service"] = InMemoryArtifactService()

for message in st.session_state.messages:
    if message["role"] == "thought":
        icon = thought_icon
        if message.get("type") == "tool_call":
            icon = tool_call_icon
        elif message.get("type") == "tool_response":
            icon = tool_response_icon

        with st.expander(message["label"], icon=icon):
            if message.get("type") == "tool_response":
                st.json(message["content"])
            else:
                st.info(message["content"])
    elif message["role"] == "artifact":
        if message.get("type") == "image":
            st.image(message["content"])
        elif message.get("type") == "plot":
            components.html(message["content"], height=600)  # type: ignore
        elif message.get("type") == "table":
            st.dataframe(message["content"], width="content", hide_index=True)

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
    artifact_service = st.session_state["artifact_service"]

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

        # check if any artifacts were added during the event
        if event.actions.artifact_delta:
            for filename, version in event.actions.artifact_delta.items():
                artifact = await artifact_service.load_artifact(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                    filename=filename,
                    version=version,
                )
                if artifact and artifact.inline_data and artifact.inline_data.mime_type:
                    if "image" in artifact.inline_data.mime_type:
                        st.image(artifact.inline_data.data)  # type: ignore
                        artifact_data = {
                            "role": "artifact",
                            "type": "image",
                            "label": "Image",
                            "content": artifact.inline_data.data,
                        }
                        st.session_state.messages.append(artifact_data)
                    elif "html" in artifact.inline_data.mime_type:
                        components.html(artifact.inline_data.data, height=600)  # type: ignore
                        artifact_data = {
                            "role": "artifact",
                            "type": "plot",
                            "label": "Plot",
                            "content": artifact.inline_data.data,
                        }
                        st.session_state.messages.append(artifact_data)
                    elif "text/csv" in artifact.inline_data.mime_type:
                        try:
                            data_bytes = bytes(artifact.inline_data.data)
                            csv_str = data_bytes.decode("utf-8")
                            df = pd.read_csv(StringIO(csv_str))
                            st.dataframe(df, width="content", hide_index=True)
                            artifact_data = {
                                "role": "artifact",
                                "type": "table",
                                "label": "Table",
                                "content": df,
                            }
                            st.session_state.messages.append(artifact_data)
                        except:
                            pass

                    else:
                        st.write(
                            f"Don't know yet how to show {artifact.inline_data.mime_type}"
                        )

        if not event.content or not event.content.parts:
            continue
        # iterate through message parts
        for part in event.content.parts:
            if part.thought:
                st.toast("Thinking", icon=":material/psychology:")
                thought_data = {
                    "role": "thought",
                    "type": "thought",
                    "label": "Thought",
                    "content": part.text,
                }
                st.session_state.messages.append(thought_data)
                with st.expander(thought_data["label"], icon=thought_icon):
                    st.info(thought_data["content"])

            elif part.function_call and include_tool_calls:
                fc = part.function_call
                thought_data = {
                    "role": "thought",
                    "type": "tool_call",
                    "label": f"Tool Call: `{fc.name}`",
                    "content": f"Arguments: `{fc.args}`",
                }
                st.session_state.messages.append(thought_data)
                with st.expander(thought_data["label"], icon=tool_call_icon):
                    st.info(thought_data["content"])

            elif part.function_response and include_tool_calls:
                fr = part.function_response
                thought_data = {
                    "role": "thought",
                    "type": "tool_response",
                    "label": f"Tool Response: `{fr.name}`",
                    "content": fr.response,
                }
                st.session_state.messages.append(thought_data)
                with st.expander(thought_data["label"], icon=tool_response_icon):
                    st.json(thought_data["content"])

            elif part.text:
                new_msg += part.text
                yield part.text

        if event.error_code:
            st.error(f"Sorry, the following error happened:\n{event.error_code}")


# --- Chat Input Block with artifact saving ---

if prompt := st.chat_input(
    "Ask me what I can do ;)", accept_file=True, file_type=[".csv", ".xlsx", ".xls"]
):
    prompt_text = prompt.text
    prompt_files = prompt.files
    if prompt_files:
        for file in prompt_files:
            file_bytes = file.read()
            mime_type = file.type
            if not mime_type and file.name.endswith(".csv"):
                mime_type = "text/csv"
            elif not mime_type and (
                file.name.endswith(".xls")
                or file.name.endswith(".xlsx")
                or file.name.endswith(".xlsm")
            ):
                mime_type = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

            asyncio.run(
                st.session_state["artifact_service"].save_artifact(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=f"{user_id}_session",
                    filename=file.name,
                    artifact=part,
                )
            )

            prompt_text += f"\n\nbiguery_agent, I’ve uploaded `{file.name}` as an artifact. Please analyze it."

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

    st.session_state.messages.append({"role": "assistant", "content": new_msg})
