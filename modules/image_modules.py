from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import os
import time
import streamlit as st
import base64
from dotenv import load_dotenv
from google.cloud import storage
from google.oauth2 import service_account
import requests
from typing import Literal

load_dotenv()

# endpoint=os.environ.get('IK_ENDPOINT', st.secrets['IK_ENDPOINT'])
endpoint = "https://storage.googleapis.com/mellanni_images"
public_key = os.environ.get("IK_PUBLIC_KEY", st.secrets["IK_PUBLIC_KEY"])
private_key = os.environ.get("IK_PRIVATE_KEY", st.secrets["IK_PRIVATE_KEY"])

imagekit = ImageKit(
    private_key=private_key, public_key=public_key, url_endpoint=endpoint
)

MAX_ATTEMPTS = 10
headers: list[str] = ["collection", "color", "size", "link", "position"]
BUCKET_NAME = "mellanni_images"


def upload_image(
    image_path: str | bytes, file_name: str, tags: list = [], folder: str | None = None
) -> str | None:
    options = UploadFileRequestOptions(
        use_unique_file_name=False,
        tags=tags if tags else [""],
        folder=f"/{folder}/" if folder else "",
    )
    if isinstance(image_path, str) and os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            image_target = image_file
    else:
        image_target = image_path
    attempts = 0
    upload = None
    error = None
    while attempts < MAX_ATTEMPTS:
        try:
            upload = imagekit.upload_file(
                file=image_target, file_name=file_name, options=options
            )
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
        return f"ERROR: {upload.message}"
    elif error:
        return f"ERROR: {error}"
    else:
        return


def upload_image_to_gcs(
    image_path: str | bytes,
    file_name: str,
    tags: dict | None = None,
    folder: str | None = None,
) -> str | None:
    """Uploads an image to Google Cloud Storage and sets its metadata."""
    bucket_name = BUCKET_NAME

    if folder:
        blob_name = f"{folder}/{file_name}"
    else:
        blob_name = file_name

    attempts = 0
    error = None
    while attempts < MAX_ATTEMPTS:
        time.sleep(0.5)
        try:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            storage_client = storage.Client(credentials=credentials)
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            blob.cache_control = "no-cache"

            if isinstance(image_path, str) and os.path.exists(image_path):
                blob.upload_from_filename(image_path)
            elif isinstance(image_path, str):
                # Download image from URL and upload to GCS
                response = requests.get(image_path)
                if response.status_code == 200:
                    error = None
                    blob.upload_from_string(response.content, content_type="image/jpeg")
                else:
                    error = response.reason
                    print(f"error for {image_path}: {error}")
                    attempts += 1
                    time.sleep(attempts)
            else:
                img_bytes = base64.b64decode(image_path)
                blob.upload_from_string(img_bytes, content_type="image/jpeg")

            if tags:
                blob.metadata = tags
                blob.patch()

            return blob.public_url
        except Exception as e:
            error = e
            time.sleep(2)
            attempts += 1

    if error:
        return f"ERROR: {error}"
    return None


@st.cache_data(ttl=3600)
def list_files(folder: str | None = None, versions: bool | None = None) -> list[dict]:
    result = []
    # list_options = ListAndSearchFileRequestOptions(path=folder if folder else '', type='file')
    files = imagekit.list_files()  # options=list_options)
    if files and files.list and len(files.list) > 0:
        blobs = [x for x in files.list]
        for blob in blobs:
            _, product, color, size, position = blob.file_path.split("/")
            result.append(
                {
                    "name": blob.name,
                    "image": blob.file_path,
                    "image_bytes": requests.get(blob.url).content if versions else None,
                    "product": product,
                    "color": color,
                    "size": size,
                    "position": position.split(".")[0],
                    "generation": blob.version_info.id,
                    "updated": blob.updated_at,
                }
            )
        return result
    else:
        return [{"ERROR": "No files found"}]


@st.cache_data(ttl=3600)
def list_files_gcs(
    folder: str | None = None, versions: bool | None = None, include_bytes: bool = False
) -> list[dict]:
    """Lists files in a GCS bucket and returns their metadata."""
    bucket_name = BUCKET_NAME
    result = []
    try:
        prefix = folder
        if prefix and not prefix.endswith("/"):
            prefix = f"{prefix}/"

        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        storage_client = storage.Client(
            credentials=credentials, project=credentials.project_id
        )
        blobs = storage_client.list_blobs(bucket_name, prefix=prefix, versions=versions)

        for blob in blobs:
            public_url = blob.public_url
            version_url = (
                f"{public_url}?generation={blob.generation}" if versions else public_url
            )
            product, color, size, position = blob.name.split("/")
            result.append(
                {
                    "name": blob.name,
                    "image": version_url,
                    "image_bytes": blob.download_as_bytes() if include_bytes else None,
                    "product": product,
                    "color": color,
                    "size": size,
                    "position": position.split(".")[0],
                    "generation": blob.generation,
                    "updated": blob.updated,
                }
            )
        return result
    except Exception as e:
        return [{"ERROR": e}]


def update_version_gcs(
    blob_name: str, blob_generation: str, action: Literal["delete", "restore"]
) -> str:
    """Deletes a specific version of a blob in GCS."""
    bucket_name = BUCKET_NAME
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        storage_client = storage.Client(
            credentials=credentials, project=credentials.project_id
        )
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name, generation=blob_generation)

        if blob.exists():
            if action == "delete":
                blob.delete()
                return f"SUCCESS: Blob {blob_name} with generation {blob_generation} deleted successfully."
            elif action == "restore":
                source_blob = bucket.blob(blob_name, generation=blob_generation)
                destination_blob = bucket.blob(blob_name)
                bucket.copy_blob(
                    source_blob,
                    bucket,
                    destination_blob.name,
                    source_generation=blob_generation,
                )
                return f"SUCCESS: Blob {blob_name} with generation {blob_generation} restored successfully."
        else:
            return f"ERROR: Blob {blob_name} with generation {blob_generation} does not exist."
    except Exception as e:
        return f"ERROR: {e}"


def delete_noncurrent_versions_gcs(folder: str | None = None) -> list[str]:
    """
    Deletes all noncurrent (older) versions of blobs in the specified GCS folder.
    Returns a list of status messages for each deleted version.
    """
    bucket_name = BUCKET_NAME
    deleted = []
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        storage_client = storage.Client(
            credentials=credentials, project=credentials.project_id
        )
        blobs = storage_client.list_blobs(bucket_name, prefix=folder, versions=True)

        # Group blobs by name, collect all generations
        blob_versions = {}
        for blob in blobs:
            if blob.name not in blob_versions:
                blob_versions[blob.name] = []
            blob_versions[blob.name].append(blob)

        for name, versions in blob_versions.items():
            # Sort by generation (latest is highest)
            versions_sorted = sorted(
                versions, key=lambda b: int(b.generation), reverse=True
            )
            # Keep the latest, delete the rest
            for old_blob in versions_sorted[1:]:
                try:
                    old_blob.delete()
                    print(f"Deleted {old_blob.name} generation {old_blob.generation}")
                    deleted.append(
                        f"Deleted {old_blob.name} generation {old_blob.generation}"
                    )
                except Exception as e:
                    print(
                        f"ERROR deleting {old_blob.name} generation {old_blob.generation}: {e}"
                    )
                    deleted.append(
                        f"ERROR deleting {old_blob.name} generation {old_blob.generation}: {e}"
                    )
        return deleted
    except Exception as e:
        return [f"ERROR: {e}"]
