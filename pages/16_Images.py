import streamlit as st
import base64
from modules.image_modules import upload_image
from modules import gcloud_modules as gc
import concurrent.futures

st.set_page_config(layout='wide', initial_sidebar_state='collapsed')

accepted_file_types = '.jpg'

from login import login_st
if login_st() and st.user.email in ('sergey@mellanni.com','ruslan@mellanni.com','bohdan@mellanni.com','vitalii@mellanni.com'):

    product_area, color_area, selector_area, size_area = st.columns([6, 6, 2, 6])
    img1_input, img2_input, img3_input, img4_input, img5_input, img6_input, img7_input, img8_input, img9_input, swtch_input = st.columns([1,1,1,1,1,1,1,1,1,1])
    img1_area, img2_area, img3_area, img4_area, img5_area, img6_area, img7_area, img8_area, img9_area, img_swtch_area = st.columns([1,1,1,1,1,1,1,1,1,1])

    def sanitize_products(product: str):
        return product.replace(' ','_').replace('/','_').replace('\\','_').lower()

    dictionary = gc.pull_dictionary()
    products = sorted(dictionary['collection'].unique().tolist())

    def push_images(img_bytes, name, product, color, sizes):
        """
        Pushes a single image to multiple folders based on size.
        This function is designed to be run in a separate thread and is pure.
        Returns a tuple containing the image name and a list of folders that failed to upload.
        """
        tags = [product, color] + sizes
        folders = [f'{product}/{color}/{size}' for size in sizes]
        failed_folders = []
        for folder in folders:
            result = upload_image(image_path=img_bytes, file_name=name, tags=tags, folder=folder)
            if result is None:
                # Extract the size from the folder path for the error message
                failed_folders.append(folder.split('/')[-1])
        return (name, failed_folders)


    # Select product and store to session state
    st.session_state.selected_product = product_area.selectbox(
        label='Select a product',
        options=products,
        placeholder='--select a product--',
        index=None)

    # If product is selected, show color options
    if st.session_state.selected_product:
        colors = sorted(dictionary[dictionary['collection']==st.session_state.selected_product]['color'].unique().tolist())

        # "Select All" checkbox for colors
        select_all_colors = selector_area.checkbox("Select All Colors")

        if select_all_colors:
            st.session_state.selected_colors = color_area.multiselect(
                label='Select a color',
                options=colors,
                placeholder='--select a color--',
                default=colors
                )
        else:
            st.session_state.selected_colors = color_area.multiselect(
                label='Select a color',
                options=colors,
                placeholder='--select a color--'
                )

    # If product and color are selected, show size options
    if 'selected_colors' in st.session_state and st.session_state.selected_colors and st.session_state.selected_product:
        sizes = sorted(
            dictionary[
                (dictionary['collection']==st.session_state.selected_product)
                &
                (dictionary['color'].isin(st.session_state.selected_colors))
                ]['size'].unique().tolist()
        )

        st.session_state.selected_sizes = size_area.multiselect(
            label='Select sizes',
            options=sizes,
            placeholder='--select sizes--',
            )
        
    image_positions = [img1_input, img2_input, img3_input, img4_input, img5_input, img6_input, img7_input, img8_input, img9_input, swtch_input]
    image_names = ['main_image', 'other_image_1', 'other_image_2', 'other_image_3', 'other_image_4', 'other_image_5', 'other_image_6', 'other_image_7', 'other_image_8', 'swatch_image']
    image_areas = [img1_area,img2_area,img3_area,img4_area,img5_area,img6_area,img7_area,img8_area,img9_area,img_swtch_area]

    if st.session_state.selected_product and st.session_state.selected_colors and st.session_state.selected_sizes:
        # st.write(f"You selected: {st.session_state.selected_product} in {st.session_state.selected_colors} color, sizes: {', '.join(st.session_state.selected_sizes)}")
        files = [position.file_uploader(label=fr"{str(i)}\. {name}") for i, (position, name) in enumerate(list(zip(image_positions, image_names)), start=1)]
        for file, image_zone in list(zip(files,image_areas)):
            if file:
                image_zone.image(file)
        
        if any([file is not None for file in files]):
            if st.button('Submit'):
                # Get session state data once in the main thread
                product = sanitize_products(st.session_state.selected_product)
                colors = [sanitize_products(x) for x in st.session_state.selected_colors]
                selected_sizes = [sanitize_products(x) for x in st.session_state.selected_sizes]
                
                failed_uploads = []
                with st.spinner('Uploading images...'):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                        futures = []
                        for file, name in zip(files, image_names):
                            if file:
                                # Read file and encode it in the main thread
                                img_obj = file.read()
                                img_bytes = base64.b64encode(img_obj)
                                # Schedule the pure function to run with all data passed as arguments
                                for color in colors:
                                    futures.append(executor.submit(push_images, img_bytes, f'{name}.jpg', product, color, selected_sizes))
                        
                        # Process results as they complete
                        for future in concurrent.futures.as_completed(futures):
                            image_name, failed_folders = future.result()
                            if failed_folders:
                                failed_uploads.append({'image': image_name, 'sizes': failed_folders})

                if not failed_uploads:
                    st.success('All files pushed successfully!')
                else:
                    st.error('Some images failed to upload. Please see details below:')
                    for failure in failed_uploads:
                        st.write(f"Image: **{failure['image']}** failed for sizes: `{', '.join(failure['sizes'])}`")