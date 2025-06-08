import streamlit as st
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional, List, Dict

from . import prompts
from vertexai.preview.vision_models import ImageGenerationModel, ImageGenerationResponse
import vertexai

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread

import time, os, json
from google.cloud import storage

SPREADSHEET_ID='1UhZplWd4sg8Mhd0Xd4Gb-6jMy2z_DYcUicEBrmJZL9M'
FOLDER_ID='1vClPSrDJi16PnvvGoSYeghcCU0WU0Sxw'
CREDS_FILE=st.secrets["gsheets-access"]
STORAGE_BUCKET='image-generations-from-agents'

VERTEX_CREDS = st.secrets['vertex_cloud_creds']
print('vertex_cloud_creds successfully retrieved')

def read_session_state(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Example structure for a before_agent_callback function.
    This callback is triggered before any logic happens inside the agent [1].
    The main reason to use this callback is to set up resources and state before the agent runs [2].

    Args:
        callback_context: Provides access to agent info, session state, etc. [3]

    Returns:
        None: To allow the agent to continue as normal [3].
        Content: To skip the agent's normal processing and return this message instead [3].
    """
    # You can access the agent name from the context [4]
    agent_name = callback_context.agent_name
    # print(f"--- Before Agent Callback running for agent: {agent_name} ---") # Example logging [4]

    # Access and modify state using callback_context.state [3-5]
    state = callback_context.state
    # Example: Initializing or updating state before the agent runs [2, 5]
    # if 'request_counter' not in state:
    #     state['request_counter'] = 0
    # state['request_counter'] += 1
    # print(f"--- State 'request_counter' updated to: {state['request_counter']} ---") # Example logging [5]

    # You can implement logic here, such as input validation or setting dynamic instructions [2, 6, 7].
    # The callback also takes llm_request: LlmRequest as an argument in before_model_callback [8],
    # but before_agent_callback primarily uses callback_context [3, 5].
    # (Note: The source [4] shows block_keyword_guardrail which uses llm_request, but it is assigned to before_model_callback [9])

    # If a condition is met where you want to skip the agent's execution and return a message [3]:
    # if some_condition_based_on_state_or_other_logic:
    #     skip_message = types.Content(
    #         role='model', # Mimic a response from the agent [4]
    #         parts=[types.Part(text='Processing skipped by before_agent_callback.')]
    #     )
    #     # print("--- Skipping agent execution due to condition ---")
    #     return skip_message # Return the message to skip [3]

    # By default, return None to allow the agent to proceed with its normal execution [3].
    # print("--- Allowing agent execution to proceed ---")
    return None


def exit_loop(tool_context: ToolContext) -> dict:
    """Call this function ONLY when the checker indicates no further changes are needed, signaling the iterative process should end."""
    print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    # Return empty dict as tools should typically return JSON-serializable output
    return {}


def create_vertexai_image(prompt_list: list[str]) -> dict:#Optional[ImageGenerationResponse|None]:
    """Creates an image or images using Vertex AI based on a text prompt(s) and saves it to Google Cloud Storage.
    
    Args:
        prompt_list (list): A list of text prompts describing images to generate.
    
    Returns:
        dict: A dictionary with 'status' (str) and 'image_url' (str) or 'error_message' (str).
    """

    vertex_creds = Credentials.from_service_account_info(VERTEX_CREDS)
    # vertex_creds = Credentials.from_service_account_file('/home/misunderstood/Downloads/creatives-agent-1a95ffd78c5d.json')

    print('Connecting bucket storage')
    client = storage.Client(credentials=vertex_creds)#project=os.environ['GC_PROJECT'])
    bucket_name = STORAGE_BUCKET  # Replace with your bucket name
    bucket = client.bucket(bucket_name)
    sub_folder = time.strftime("%Y-%m-%dT%H:%M:%S")
    result = {'status':'success'}


    print('Connecting vertexAI')
    vertexai.init(project='creatives-agent')#, location='us-east1')
    
    
    generation_model = ImageGenerationModel.from_pretrained("imagen-4.0-generate-preview-05-20")
    for pn, prompt in enumerate(prompt_list, start=1):
        print(f'Generating prompt {pn}\n\n\n\n\n')
        try:
            images = generation_model.generate_images(
                prompt=prompt,
                number_of_images=2,
                aspect_ratio="9:16",
                negative_prompt="",
                person_generation="allow_all",
                # safety_filter_level="block_fewest",
                add_watermark=True,
            )
            for i, image in enumerate(images):
                image_name = f'image{pn}_{i}.png'
                image.save(image_name)
                blob = bucket.blob(f'{sub_folder}/image{pn}_{i}.png')

                blob.upload_from_filename(image_name)
                result[image_name] = f'https://storage.googleapis.com/{bucket_name}/{sub_folder}/image{pn}_{i}.png'
                os.remove(image_name)
            time.sleep(1)
        except Exception as e:
            print(f'\n\n______Error while generating images: {e}\n\n')
            result[f'failed prompt {pn}'] = f'prompt {prompt} failed'
    result['status'] = f'Images saved to https://storage.googleapis.com/{bucket_name}/{sub_folder} bucket'
    return result


def read_write_google_sheet(callback_context: CallbackContext) -> None:#Optional[types.Content]:
    """
    Write data to a Google Spreadsheet.
    A function used at the end of the conversation to record all the session state keys
    
    Parameters:
    - callback_context - a CallbackContext object containing all the session data
    
    Returns:
    - None.
    """

    state = callback_context.state
    if not all([prompts.INITIAL_STORYLINES in state, prompts.CAPTIONS_TEXT in state, prompts.IMAGE_PROMPT in state]):
        print('\n\n\n' + "keys not found" + '\n\n\n')
        return
    storyline = state.get(prompts.INITIAL_STORYLINES)
    captions = state.get(prompts.CAPTIONS_TEXT)
    img_prompts = state.get(prompts.IMAGE_PROMPT)
    date = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        # creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scope)
        creds = Credentials.from_service_account_info(CREDS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet('Sheet1')
        read_data = worksheet.get("A:E")
        update_range = f"A{len(read_data)+1}:E{len(read_data)+1}"
        
        worksheet.update([[date, storyline, captions, img_prompts]], update_range)
        
        # print('#'* 50)
        print( {'status':'success'}) 
        return None
    
    except gspread.exceptions.SpreadsheetNotFound:
        # print('#'* 50)
        print( {'status':'Error: Spreadsheet not found. Check the spreadsheet ID.'}) 
        return None
    except gspread.exceptions.WorksheetNotFound:
        # print('#'* 50)
        print( {'status': 'Error: Worksheet not found. Check the sheet name.'}) 
        return None
    except Exception as e:
        # print('#'* 50)
        print( {'status': f'Error: {str(e)}'}) 
        return None

# def manage_drive_folder(callback_context: CallbackContext):
#     """
#     Create a folder in a specified Google Shared Drive folder and upload a file to it.
    
#     Parameters:
#     - folder_name (str): Name of the new folder to create.
#     - file_path (str): Local path to the file to upload.
#     - file_name (str): Name for the file in Google Drive.
    
#     Returns:
#     - tuple: (new_folder_id, uploaded_file_id) or (None, None) if an error occurs.
#     """
#     try:
#         # Authenticate with service account
#         scopes = ['https://www.googleapis.com/auth/drive']
#         creds = Credentials.from_service_account_file('.secrets/creatives-agent-.json', scopes=scopes)
#         service = build('drive', 'v3', credentials=creds)
        
#         # Create a new folder in the Shared Drive
#         folder_metadata = {
#             'name': folder_name,
#             'mimeType': 'application/vnd.google-apps.folder',
#             'parents': [FOLDER_ID]
#         }
#         folder = service.files().create(
#             body=folder_metadata, 
#             fields='id',
#             supportsAllDrives=True
#         ).execute()
#         new_folder_id = folder.get('id')
#         print(f"Created folder '{folder_name}' with ID: {new_folder_id}")
        
#         # Upload file to the new folder in the Shared Drive
#         file_metadata = {
#             'name': file_name,
#             'parents': [new_folder_id]
#         }
#         media = MediaFileUpload(file_path)
#         file = service.files().create(
#             body=file_metadata,
#             media_body=media,
#             fields='id',
#             supportsAllDrives=True
#         ).execute()
#         file_id = file.get('id')
#         print(f"Uploaded file '{file_name}' with ID: {file_id}")
        
#         return new_folder_id, file_id
    
#     except Exception as e:
#         print(f"Error: {str(e)}")
#         return None, None
    
