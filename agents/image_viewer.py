from google.adk.agents import Agent

from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam

from modules.gspread_recorder import read_write_google_sheet

import os, json
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


OPENAI_KEY = os.environ.get('OPENAI_AGENTS_API_KEY')
from data import MODEL

def image_viewer_tool(question: str, links: list[str]) -> dict:
    """
    A function that processes image processing and extracts data from images based on the question.
    
    Args:
        question (str): Question to ask about the images.
        links (list): List of image URLs to view.
    
    Returns:
        list: List of processed image insights.
    """

    client = OpenAI(api_key=OPENAI_KEY)
    result = {}
    for link in links:
        msgs: list[ChatCompletionUserMessageParam] = [
                    {
                    "role": "user","content": [
                        {"type": "text","text": f"{question} " "Reply in JSON format: {'url':the link of the image, 'description':image description}"},
                        {"type": "image_url","image_url": {"url": link}},
                        ]
                    }
        ]
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=msgs,
                response_format = {"type": "json_object"}
            )
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                value = json.loads(response.choices[0].message.content)
                result[link] = value['description']
            else:
                result[link] = "No insight for image"
            try:
                read_write_google_sheet([link, result[link]])
            except Exception as e:
                print("$" * 50)
                print(f"Error writing to Google Sheet: {e}")
        except Exception as e:
            print(f"Error processing image {link}: {e}")
            result[link] = f"Error: {str(e)}"

    return result

def create_image_viewer_agent():
    image_viewer_agent = Agent(
        model=MODEL,
        name='image_viewer',
        description='An agent that can view and analyze images, answer questions about them, and provide insights based on their content.',
        instruction="""
    You can view images and provide insights about them. You MUST use the `image_viewer_tool` to process images.
    If the user is asking about images, you MUST ensure that you have links to the images or files containing links to images.
    A user may submit a link in the text, or they can upload a file with links to images.
    Once the images are processed, notify the user that the information has been saved to this Google Sheet: https://docs.google.com/spreadsheets/d/1SpFOarsVGLiVIYhslAYCVZwAGBHqn55j0LJMAn_Wwv0/edit?gid=0#gid=0
    """,
        tools=[image_viewer_tool],
        output_key='IMAGE_VIEWER_RESULT',
        )
    return image_viewer_agent