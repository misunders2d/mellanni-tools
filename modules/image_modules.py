from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio.models.ListAndSearchFileRequestOptions import ListAndSearchFileRequestOptions
import os
import streamlit as st
from dotenv import load_dotenv
load_dotenv()


endpoint=os.environ.get('IK_ENDPOINT')
public_key=os.environ.get('IK_PUBLIC_KEY')
private_key=os.environ.get('IK_PRIVATE_KEY')

imagekit = ImageKit(
    private_key=private_key,
    public_key=public_key,
    url_endpoint = endpoint
)


def upload_image(image_path:str|bytes, file_name:str, tags:list=[], folder:str|None=None) -> str | None:
    # metadata = json.dumps([{"Field label":"1800", "Field name":"new", "Field type":"Text"}])
    options=UploadFileRequestOptions(
        use_unique_file_name=False,
        tags=tags if tags else [''],
        folder=f"/{folder}/" if folder else '',
        # overwrite_custom_metadata=True,
        # custom_metadata=json.loads(metadata)
        )
    try:
        if isinstance(image_path, str):
            with open(image_path, "rb") as image_file:
                upload = imagekit.upload_file(file=image_file, file_name=file_name, options=options)
        else:
            upload = imagekit.upload_file(file=image_path, file_name=file_name, options=options)
        if upload.is_error:
            print("Error uploading image:", upload.message)
            return None
        else:
            print(f"Image uploaded successfully:\n{upload.url}")
            return upload.url
    except Exception as e:
        print(f"Error while uploading file: {e}")

# url = upload_image('/home/misunderstood/Downloads/main1.jpg', 'main_image.jpg', tags=['test'], folder='/trying3/folder/another folder/')

def list_files(folder:str|None=None):
    list_options = ListAndSearchFileRequestOptions(path=folder if folder else '')
    files = imagekit.list_files(options=list_options)
    if files and files.list and len(files.list) > 0:
        print([(x.name, x.url) for x in files.list])
        return files.list[0]

# img = list_files(folder='test')
# print(img.custom_metadata)