from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio.models.ListAndSearchFileRequestOptions import ListAndSearchFileRequestOptions
import os
import time
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

endpoint=os.environ.get('IK_ENDPOINT', st.secrets['IK_ENDPOINT'])
public_key=os.environ.get('IK_PUBLIC_KEY', st.secrets['IK_PUBLIC_KEY'])
private_key=os.environ.get('IK_PRIVATE_KEY', st.secrets['IK_PRIVATE_KEY'])

imagekit = ImageKit(
    private_key=private_key,
    public_key=public_key,
    url_endpoint = endpoint
)


def upload_image(image_path:str|bytes, file_name:str, tags:list=[], folder:str|None=None) -> str | None:
    options=UploadFileRequestOptions(
        use_unique_file_name=False,
        tags=tags if tags else [''],
        folder=f"/{folder}/" if folder else '',
        )
    if isinstance(image_path, str) and os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            image_target = image_file
    else:
        image_target = image_path
    attempts = 0
    upload = None
    error = None
    while attempts < 5:
        try:
            upload = imagekit.upload_file(file=image_target, file_name=file_name, options=options)
            if upload and not upload.is_error:
                return upload.url
            elif upload and upload.is_error:
                time.sleep(2)
                attempts += 1
        except Exception as e:
            error = e
            time.sleep(2)
            attempts += 1

    if upload and upload.is_error:
        return f'ERROR: {upload.message}'
    elif error:
        return f'ERROR: {error}'
    else:
        return



def list_files(folder:str|None=None):
    result = [['collection','color','size','link', 'position']]
    list_options = ListAndSearchFileRequestOptions(path=folder if folder else '', type='file')
    files = imagekit.list_files()#options=list_options)
    if files and files.list and len(files.list) > 0:
        images = [x.file_path for x in files.list]
        for image in images:
            _, product, color, size, position = image.split('/')
            result.append([product, color, size, f'{endpoint}{image}', position.split('.')[0]])
        return result
