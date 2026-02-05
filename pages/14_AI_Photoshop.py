from google import genai
from PIL import Image
from io import BytesIO
import streamlit as st
from streamlit_image_comparison import image_comparison
from typing import Any

st.set_page_config(
    page_title="AI photoshop",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def calculate_cost(response):
    try:
        input_tokens = 0
        if response.usage_metadata and response.usage_metadata.prompt_token_count:
            input_tokens += response.usage_metadata.prompt_token_count

        output_tokens = 0
        if response.usage_metadata and response.usage_metadata.candidates_token_count:
            output_tokens += response.usage_metadata.candidates_token_count

        total_cost = (input_tokens * 0.30 / 1_000_000) + 0.039
        return total_cost
    except Exception as e:
        return str(e)


def generate_prompt(
    master_prompt, base_image=None, reference_images: dict | None = None
):

    contents = [master_prompt]
    if base_image:
        contents.append(base_image)
    if reference_images:
        for image in reference_images.values():
            contents.append(image["text"])
            contents.append(image["image"])
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
            return
        total_cost = calculate_cost(response=response)
        image_parts = [
            part.inline_data.data
            for part in response.candidates[0].content.parts
            if part.inline_data
        ]

        if image_parts and isinstance(image_parts[0], bytes):
            image = Image.open(BytesIO(image_parts[0]))
            return image, total_cost
    except Exception as e:
        st.warning(f"Sorry, an error occurred: {e}")
        return


bedroom_tab, photoshop_tab = st.tabs(["Bedrom decor", "Photoshop"])
with bedroom_tab:
    bedroom_tab.subheader(
        "Get instant bedroom decor suggestions. Simply upload a picture of your bedroom!"
    )
    _, preview_column, _ = st.columns([2, 4, 2])
    preview_area = preview_column.empty()
    _, base_image_colum, _, result_image_colum, _ = st.columns([2, 4, 2, 4, 2])

    if st.toggle("Use your camera to take a picture of your bedroom", value=False):
        image_to_use = st.camera_input(
            "Or take a picture of your bedroom",
            key="file_uploader",
        )
    else:
        image_to_use = st.file_uploader(
            "Upload a picture of your bedroom",
            type=["png", "jpg", "jpeg", "webp"],
            key="file_uploader",
        )
    if image_to_use is not None:
        base_image = Image.open(image_to_use)
        master_prompt = (
            """
            You are an expert in bedroom decor, specifically in color matching, items matching and overall design.
            Below you will find an image of a bedroom that needs to be redecorated.
            Make sure to research all the latest trends in bedroom decor and come up with a modern, stylish and cozy design.

            Here is the image of a bedroom.
            Do not make any changes to bed frame or walls, but modify the colors and bedding items.
            Important! If the image does not contain bedroom, inform the user that the image is not valid and ask for a new one.
        """,
        )

        contents = generate_prompt(master_prompt, base_image)
        preview_area.image(base_image, caption="Original image")
        if st.button("Generate decor suggestions"):
            with st.spinner("Generating decor suggestions..."):
                generation = generate_suggestted_decor(contents)
                if not generation:
                    st.error(
                        "Failed to generate the decor suggestions. Please try again."
                    )
                else:
                    final_image, total_cost = generation
                    base_image_colum.image(base_image)
                    result_image_colum.image(
                        final_image,
                        caption="Suggested decor",
                    )
                    with preview_area:
                        image_comparison(
                            img1=base_image,  # type: ignore
                            img2=final_image,  # type: ignore
                            label1="Original image",
                            label2="Suggested decor",
                            make_responsive=True,
                            width=800,
                            starting_position=80,
                        )

    else:
        st.info("Please upload (or take a picture of) a bedroom image to proceed.")

with photoshop_tab:
    photoshop_tab.subheader("Prototype anything with AI photoshop")
    prompt_kwargs: dict[str, Any] = {}

    input_cols, result_cols = st.columns([2, 4])
    prompt_input = input_cols.text_area(label="What do you want to do?")
    prompt_kwargs = {"master_prompt": prompt_input}
    main_image_input = input_cols.file_uploader(
        "Upload the image you want to edit (optional)", type=["jpg", "jpeg", "png"]
    )
    if main_image_input is not None:
        main_image = Image.open(main_image_input)
        input_cols.image(main_image)
        prompt_kwargs["base_image"] = main_image

    reference_images_input = input_cols.file_uploader(
        label="Upload reference images, if any",
        accept_multiple_files=True,
        type=["jpg", "jpeg", "png"],
    )

    if reference_images_input:
        reference_images = {}
        for i, reference_image in enumerate(reference_images_input):
            ref_image = Image.open(reference_image)
            input_cols.image(ref_image)
            ref_text = input_cols.text_input(label="what is this image for?", key=i)
            reference_images[i] = {"text": ref_text, "image": ref_image}
            input_cols.divider()
        prompt_kwargs["reference_images"] = reference_images

    if result_cols.button(label="Generate!", type="primary"):
        if not prompt_input:
            st.warning("No prompt detected.")
            st.stop()

        contents = generate_prompt(**prompt_kwargs)
        with st.spinner("Please wait, NanoBanana is working..."):
            generation = generate_suggestted_decor(contents=contents)
            if not generation:
                result_cols.error(
                    "Failed to generate the decor suggestions. Please try again."
                )
            else:
                result, total_cost = generation
                result_cols.image(result)
                result_cols.write(f"Total cost for the generation: ${total_cost:.5f}")
