from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio.models.ListAndSearchFileRequestOptions import ListAndSearchFileRequestOptions
import os
import time
import streamlit as st
import base64
from dotenv import load_dotenv
from google.cloud import storage
from google.oauth2 import service_account

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
    while attempts < 10:
        try:
            upload = imagekit.upload_file(file=image_target, file_name=file_name, options=options)
            if upload and not upload.is_error:
                return upload.url
            elif upload and upload.is_error:
                attempts += 1
                time.sleep(attempts)
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


def upload_image_to_gcs(image_path: str | bytes, file_name: str, tags: dict | None = None, folder: str | None = None) -> str | None:
    """Uploads an image to Google Cloud Storage and sets its metadata."""
    bucket_name = "mellanni_images"
    
    if folder:
        blob_name = f"{folder}/{file_name}"
    else:
        blob_name = file_name

    attempts = 0
    error = None
    while attempts < 10:
        try:
            credentials = service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'])
            storage_client = storage.Client(credentials=credentials)
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            if isinstance(image_path, str) and os.path.exists(image_path):
                blob.upload_from_filename(image_path)
            else:
                img_bytes = base64.b64decode(image_path)
                blob.upload_from_string(img_bytes, content_type='image/jpeg')

            if tags:
                blob.metadata = tags
                blob.patch()

            return blob.public_url
        except Exception as e:
            error = e
            time.sleep(2)
            attempts += 1
    
    if error:
        return f'ERROR: {error}'
    return None


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


def list_files_gcs(folder: str | None = None):
    """Lists files in a GCS bucket and returns their metadata."""
    bucket_name = "mellanni_images"
    result = [['collection','color','size','link', 'position']]
    try:
        credentials = service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'])
        storage_client = storage.Client(credentials=credentials)
        blobs = storage_client.list_blobs(bucket_name, prefix=folder)

        for blob in blobs:
            product, color, size, position = blob.name.split('/')
            image = f'{endpoint}/{blob.name}'
            result.append([product, color, size, image, position.split('.')[0]])
        return result
    except Exception as e:
        return [[f'ERROR: {e}']]