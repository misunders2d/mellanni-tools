from google import genai
from PIL import Image
from io import BytesIO
import streamlit as st

st.set_page_config(
    page_title="Bedroom Decor Suggestions",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.subheader(
    "Get instant bedroom decor suggestions. Simply upload a picture of your bedroom!"
)


def generate_prompt(base_image, reference_images: dict):

    contents = [
        """
            You are an expert in bedroom decor, specifically in color matching, items matching and overall design.
            Below you will find an image of a bedroom that needs to be redecorated.
            Make sure to research all the latest trends in bedroom decor and come up with a modern, stylish and cozy design.
        """,
        """
            Here is the image of a bedroom.
            Do not make any changes to bed frame or walls, but modify the colors and bedding items.
            Important! If the image does not contain bedroom, inform the user that the image is not valid and ask for a new one.
        """,
        base_image,
    ]
    return contents


def generate_suggestted_decor(contents: list):
    try:
        client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"], vertexai=False)

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents,
        )
        if (
            not response.candidates
            or not response.candidates[0].content
            or not response.candidates[0].content.parts
        ):
            return None
        image_parts = [
            part.inline_data.data
            for part in response.candidates[0].content.parts
            if part.inline_data
        ]

        if image_parts and isinstance(image_parts[0], bytes):
            image = Image.open(BytesIO(image_parts[0]))
            return image
    except Exception as e:
        st.warning(f"Sorry, an error occurred: {e}")


base_image_colum, result_image_colum = st.columns(2)
base_image_area = base_image_colum.empty()
if st.toggle("Use your camera to take a picture of your bedroom", value=False):
    image_to_use = base_image_colum.camera_input("Or take a picture of your bedroom")
else:
    image_to_use = base_image_colum.file_uploader(
        "Upload a picture of your bedroom", type=["png", "jpg", "jpeg"]
    )
if image_to_use is not None:
    base_image = Image.open(image_to_use)
    contents = generate_prompt(base_image, reference_images={})
    base_image_area.image(base_image, caption="Original image")
    if st.button("Generate decor suggestions"):
        with st.spinner("Generating decor suggestions..."):
            final_image = generate_suggestted_decor(contents)
            if not final_image:
                st.error("Failed to generate the decor suggestions. Please try again.")
            else:
                result_image_colum.image(
                    final_image,
                    caption="Suggested decor",
                )

else:
    st.info("Please upload (or take a picture of) a bedroom image to proceed.")
