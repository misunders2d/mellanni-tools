import base64
import json
from io import BytesIO
from typing import Any

import streamlit as st
from google import genai
from google.genai.types import (
    GenerateContentConfig,
    ImageConfig,
    ThinkingConfig,
    ThinkingLevel,
)
from openai import OpenAI
from PIL import Image
from streamlit_image_comparison import image_comparison

st.set_page_config(
    page_title="AI photoshop",
    page_icon="media/logo.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = ""
if "gemini_result" not in st.session_state:
    st.session_state.gemini_result = None
if "openai_result" not in st.session_state:
    st.session_state.openai_result = None
IMAGE_MODEL = "gemini-3.1-flash-image-preview"  # "gemini-2.5-flash-image"
OPENAI_IMAGE_MODEL = "gpt-image-2"

MODEL_NANOBANANA = "Nanobanana (Gemini)"
MODEL_GPT_IMAGE = "GPT Image (OpenAI)"

OPENAI_SIZES = {
    "1024x1024 (square)": "1024x1024",
    "1536x1024 (landscape)": "1536x1024",
    "1024x1536 (portrait)": "1024x1536",
    "2048x2048 (2K square)": "2048x2048",
    "2048x1152 (2K landscape)": "2048x1152",
    "3840x2160 (4K landscape)": "3840x2160",
    "2160x3840 (4K portrait)": "2160x3840",
    "auto": "auto",
}

OPENAI_QUALITIES = ["auto", "low", "medium", "high"]

# gpt-image-2 per-million-token pricing (USD).
OPENAI_PRICE_TEXT_IN = 5.00
OPENAI_PRICE_TEXT_CACHED = 1.25
OPENAI_PRICE_IMAGE_IN = 8.00
OPENAI_PRICE_IMAGE_CACHED = 2.00
OPENAI_PRICE_IMAGE_OUT = 30.00
PROMPT_EXAMPLE = {
    "composition_and_spatial_geometry": {
        "camera_angle": "Three-quarter perspective, 15-degree low-angle tilt looking up from the front-left corner of the mattress.",
        "focal_point": "Coordinate [x:350, y:650] (Front-left quilted corner of the bedspread).",
        "spatial_depth_planes": {
            "foreground": "Sharp focus on the draping 'waterfall' fold of the teal quilt [x:100, y:800].",
            "midground": "Layered pillows and the top fold of the bedding [x:500, y:400].",
            "background": "Soft bokeh on the button-tufted headboard and side tables [x:500, y:200].",
        },
        "shapes": "Repeating chevron/herringbone quilted patterns; soft organic 'S' curves in the fabric folds; rigid rectangular lines of the nightstand; circular geometry of the new lamp base.",
    },
    "product_details_and_materials": {
        "primary_item": {
            "label": "Quilted Bedspread",
            "material": "High-luster crushed velvet with a dense, short-pile nap. Fiber density: 300 GSM.",
            "color": "Deep Peacock Teal (HEX: #006666). Color depth varies with light from Cyan-Green to Forest Shadow.",
            "texture": "Raised 3D quilted stitching in a rhythmic leaf/chevron pattern. Threads are high-strength polyester with a slight satin sheen.",
            "physics": "Heavy drape weight; soft, rounded edges on folds; no sharp creases.",
        },
        "layering_materials": [
            {
                "item": "Euro Shams (Back)",
                "material": "Stone-washed Belgian linen.",
                "color": "Antique Ivory (HEX: #F5F5DC).",
                "shape": "Large 26x26 squares, slightly overstuffed for volume.",
            },
            {
                "item": "Standard Shams (Front)",
                "material": "Matching Peacock Teal velvet.",
                "shape": "Rectangular 20x26 with a 2-inch flanged edge.",
            },
            {
                "item": "Accent Throw",
                "material": "Chunky-knit Merino wool (1-inch thick yarn).",
                "color": "Soft Cream (HEX: #FFFDD0).",
                "placement": "Folded diagonally across the bottom-right foot of the bed.",
            },
        ],
    },
    "lighting_and_chromatic_atmosphere": {
        "primary_light": {
            "type": "Key Light (Natural Window)",
            "color_temp": "3200K (Warm Amber/Golden Hour).",
            "direction": "45-degree angle from the right side of the frame.",
            "effect": "Specular highlights on the 'peaks' of the quilted velvet; deep occlusion shadows in the 'valleys'.",
        },
        "secondary_light": {
            "type": "Rim Light",
            "color": "Cool White (5500K).",
            "placement": "Back-left behind the headboard to create a thin halo silhouette, separating the bed from the wall.",
        },
        "global_illumination": "Soft bounce light from the ivory rug (implied) to fill the shadows on the left side of the bed.",
    },
    "environmental_props_and_surfaces": {
        "headboard": {
            "material": "Faux-leather or high-end vinyl upholstery with a matte finish.",
            "color": "Champagne Beige (HEX: #D7C4A3).",
            "shape": "Scalloped-top rectangular with diamond-pattern button tufting.",
            "frame": "Brushed Champagne Gold metallic trim (satin finish, non-reflective).",
        },
        "nightstand_right": {
            "surface": "High-gloss white lacquer over MDF.",
            "hardware": "Linear brushed brass handle.",
            "props": [
                {
                    "item": "Table Lamp",
                    "material": "Fluted smoke-gray glass base with a black linen drum shade.",
                    "color": "Charcoal and Translucent Gray.",
                },
                {
                    "item": "Decor",
                    "material": "Matte ceramic tray with two gold-rimmed coasters.",
                },
            ],
        },
        "wall_treatment": {
            "material": "Matte eggshell paint over wood wainscoting.",
            "color": "Warm Greige (HEX: #E1DBD2).",
            "shape": "Sunken rectangular panels with beveled molding.",
        },
    },
    "technical_rendering_intent": {
        "engine_style": "Ray-traced, path-traced rendering (Cycles/V-Ray).",
        "post_processing": "Subtle bloom on highlights; 5% grain for film-like texture; chromatic aberration at the extreme edges of the frame for realism.",
    },
}


def calculate_cost(response, resolution, image=True):
    price_dict = {"512": 0.045, "1K": 0.067, "2K": 0.101, "4K": 0.151}
    try:
        input_tokens = 0
        if response.usage_metadata and response.usage_metadata.prompt_token_count:
            input_tokens += response.usage_metadata.prompt_token_count

        output_tokens = 0
        if response.usage_metadata and response.usage_metadata.candidates_token_count:
            output_tokens += response.usage_metadata.candidates_token_count

        image_cost = price_dict.get(resolution, 0) if image else 0

        total_cost = (input_tokens * 0.5 / 1_000_000) + image_cost
        return total_cost
    except Exception as e:
        return str(e)


def update_current_prompt(new_prompt: str):
    st.session_state.current_prompt = new_prompt


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


def generate_suggestted_decor(contents: list, improve_prompt=False):
    try:
        client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"], vertexai=False)
        config = (
            GenerateContentConfig(
                thinking_config=ThinkingConfig(
                    thinking_level=ThinkingLevel(value=thinking),
                ),
                image_config=ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution,
                ),
                response_modalities=[
                    "IMAGE",
                    "TEXT",
                ],
            )
            if not improve_prompt
            else GenerateContentConfig(response_mime_type="application/json")
        )

        response = client.models.generate_content(
            model=IMAGE_MODEL, contents=contents, config=config
        )
        if (
            not response.candidates
            or not response.candidates[0].content
            or not response.candidates[0].content.parts
        ):
            return
        total_cost = calculate_cost(
            response=response, resolution=resolution, image=not improve_prompt
        )
        image_parts = [
            part.inline_data.data
            for part in response.candidates[0].content.parts
            if part.inline_data
        ]

        texts = [
            part.text for part in response.candidates[0].content.parts if part.text
        ]

        if image_parts and isinstance(image_parts[0], bytes):
            image = Image.open(BytesIO(image_parts[0]))
            return image, total_cost
        if texts:
            return "".join(texts), total_cost

    except Exception as e:
        st.warning(f"Sorry, an error occurred: {e}")
        return


def _gpt_image_2_cost(usage) -> float:
    """Compute USD cost from gpt-image-2 usage tokens. Returns 0 when usage is absent."""
    if usage is None:
        return 0.0

    def _get(obj, name: str) -> int:
        if obj is None:
            return 0
        # handle both pydantic model attributes and extras dict
        val = getattr(obj, name, None)
        if val is None:
            extra = getattr(obj, "model_extra", None) or {}
            val = extra.get(name, 0)
        return int(val or 0)

    details_in = getattr(usage, "input_tokens_details", None)
    details_out = getattr(usage, "output_tokens_details", None)

    text_in = _get(details_in, "text_tokens")
    image_in = _get(details_in, "image_tokens")
    cached_text = _get(details_in, "cached_text_tokens")
    cached_image = _get(details_in, "cached_image_tokens")

    if details_out is not None:
        image_out = _get(details_out, "image_tokens")
    else:
        image_out = _get(usage, "output_tokens")

    return (
        text_in * OPENAI_PRICE_TEXT_IN
        + cached_text * OPENAI_PRICE_TEXT_CACHED
        + image_in * OPENAI_PRICE_IMAGE_IN
        + cached_image * OPENAI_PRICE_IMAGE_CACHED
        + image_out * OPENAI_PRICE_IMAGE_OUT
    ) / 1_000_000


def generate_openai_image(
    master_prompt, base_image=None, reference_images: dict | None = None
):
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_IMAGE_API_KEY"])
        size = openai_size
        quality = openai_quality

        prompt = master_prompt[0] if isinstance(master_prompt, tuple) else master_prompt
        image_inputs = []

        if base_image is not None:
            buf = BytesIO()
            base_image.save(buf, format="PNG")
            buf.seek(0)
            buf.name = "base.png"
            image_inputs.append(buf)

        if reference_images:
            for i, ref in enumerate(reference_images.values(), 1):
                caption = ref.get("text") or ""
                if caption:
                    prompt += f"\n\nReference image {i}: {caption}"
                buf = BytesIO()
                ref["image"].save(buf, format="PNG")
                buf.seek(0)
                buf.name = f"reference_{i}.png"
                image_inputs.append(buf)

        common = dict(
            model=OPENAI_IMAGE_MODEL,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )

        if image_inputs:
            response = client.images.edit(
                image=image_inputs if len(image_inputs) > 1 else image_inputs[0],
                **common,
            )
        else:
            response = client.images.generate(**common)

        if not response.data or not response.data[0].b64_json:
            return

        image = Image.open(BytesIO(base64.b64decode(response.data[0].b64_json)))
        total_cost = _gpt_image_2_cost(getattr(response, "usage", None))
        return image, total_cost
    except Exception as e:
        st.warning(f"Sorry, an error occurred: {e}")
        return


def generate_image(
    master_prompt, base_image=None, reference_images=None, improve_prompt=False
):
    if improve_prompt or image_model == MODEL_NANOBANANA:
        contents = generate_prompt(master_prompt, base_image, reference_images)
        return generate_suggestted_decor(contents, improve_prompt=improve_prompt)
    return generate_openai_image(
        master_prompt=master_prompt,
        base_image=base_image,
        reference_images=reference_images,
    )


image_model = st.radio(
    "Image model",
    options=[MODEL_NANOBANANA, MODEL_GPT_IMAGE],
    horizontal=True,
    help="GPT Image uses OpenAI's gpt-image-2. 'Help me write' always uses Gemini.",
)

# Defaults so bedroom_tab's generation path works before photoshop_tab renders.
aspect_ratio = "1:1"
thinking = "MINIMAL"
resolution = "1K"
openai_size = "1024x1024"
openai_quality = "auto"

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

        preview_area.image(base_image, caption="Original image")
        if st.button("Generate decor suggestions"):
            with st.spinner("Generating decor suggestions..."):
                generation = generate_image(
                    master_prompt=master_prompt, base_image=base_image
                )
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
    selector_row = photoshop_tab.empty()
    if image_model == MODEL_NANOBANANA:
        prompt_input_col, aspect_ratio_col, thinking_col, resolution_col = (
            selector_row.columns([4, 1, 1, 1])
        )
        aspect_ratio = aspect_ratio_col.selectbox(
            label="Select aspect ratio",
            options=[
                "1:1",
                "16:9",
                "1:4",
                "1:8",
                "2:3",
                "3:2",
                "3:4",
                "4:1",
                "4:3",
                "4:5",
                "5:4",
                "8:1",
                "9:16",
                "16:9",
                "21:9",
            ],
        )
        thinking = thinking_col.selectbox(
            label="Select thinking effort", options=["MINIMAL", "HIGH"]
        )
        resolution = resolution_col.selectbox(
            label="Select resolution", options=["512", "1K", "2K", "4K"]
        )
    else:
        prompt_input_col, size_col, quality_col = selector_row.columns([4, 1, 1])
        openai_size_label = size_col.selectbox(
            label="Select size", options=list(OPENAI_SIZES.keys())
        )
        openai_size = OPENAI_SIZES[openai_size_label]
        openai_quality = quality_col.selectbox(
            label="Select quality", options=OPENAI_QUALITIES
        )
    prompt_kwargs: dict[str, Any] = {}

    input_cols, result_cols = st.columns([2, 4])
    prompt_input = prompt_input_col.text_area(
        label="What do you want to do?",
        value=st.session_state.current_prompt,
    )
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

        spinner_label = (
            "Please wait, NanoBanana is working..."
            if image_model == MODEL_NANOBANANA
            else "Please wait, gpt-image-2 is working..."
        )
        with st.spinner(spinner_label):
            generation = generate_image(**prompt_kwargs)
            if not generation:
                result_cols.error(
                    "Failed to generate the decor suggestions. Please try again."
                )
            else:
                slot = (
                    "gemini_result"
                    if image_model == MODEL_NANOBANANA
                    else "openai_result"
                )
                st.session_state[slot] = generation

    gemini_col, openai_col = result_cols.columns(2)
    if st.session_state.gemini_result is not None:
        img, cost = st.session_state.gemini_result
        gemini_col.image(img, caption="Nanobanana (Gemini)")
        gemini_col.write(f"Cost: ${cost:.5f}")
        if gemini_col.button("Clear Gemini", key="clear_gemini"):
            st.session_state.gemini_result = None
            st.rerun()
    if st.session_state.openai_result is not None:
        img, cost = st.session_state.openai_result
        openai_col.image(img, caption="GPT Image (OpenAI)")
        openai_col.write(f"Cost: ${cost:.5f}")
        if openai_col.button("Clear OpenAI", key="clear_openai"):
            st.session_state.openai_result = None
            st.rerun()
    if result_cols.button(label="Help me write", type="secondary"):
        improve_kwargs = dict(prompt_kwargs)
        improve_kwargs["master_prompt"] = (
            prompt_kwargs["master_prompt"]
            + f"""\nGenerate the JSON structured prompt which includes ALL the improved image details.
        Everything must be described, including, but not limited to, colors, shapes, materials, facial expressions, mood, lighing, interior, style etc.

        Refer to this example: {PROMPT_EXAMPLE}.

        Do not mention resolution or aspect raio"""
        )
        with st.spinner("Please wait, generating a structured prompt..."):
            generation = generate_image(**improve_kwargs, improve_prompt=True)
            if not generation:
                result_cols.error(
                    "Failed to generate the decor suggestions. Please try again."
                )
            else:
                result, total_cost = generation
                if isinstance(result, str):
                    update_current_prompt(new_prompt=prompt_input + "\n" + result)
                    st.write("Check the updated prompt in the input window")
                    st.rerun()
