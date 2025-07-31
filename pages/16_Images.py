import streamlit as st
import pandas as pd
import base64
from numpy import nan
from modules.image_modules import upload_image, list_files, upload_image_to_gcs, list_files_gcs
from modules import gcloud_modules as gc
import concurrent.futures

st.set_page_config(layout='wide', initial_sidebar_state='collapsed')

ACCEPTED_FILE_TYPES = '.jpg'
MAX_WORKERS=5

from login import login_st
if login_st() and st.user.email in ('sergey@mellanni.com','ruslan@mellanni.com','bohdan@mellanni.com','vitalii@mellanni.com'):
    main_area, selector_area = st.columns([10, 2])
    target: str = selector_area.radio(
        'Select storage', options=['imagekit', 'gcs'], index=1, horizontal=False,
        help='We have two options for image storage, but regardless of the option the links are the same.'
        )
    with st.expander('Upload images', expanded=True, icon=":material/image_arrow_up:"):
        product_area, color_area, selector_area, size_area = main_area.columns([6, 6, 2, 6])
        img1_input, img2_input, img3_input, img4_input, img5_input, img6_input, img7_input, img8_input, img9_input, swtch_input = main_area.columns([1,1,1,1,1,1,1,1,1,1])
        img1_area, img2_area, img3_area, img4_area, img5_area, img6_area, img7_area, img8_area, img9_area, img_swtch_area = main_area.columns([1,1,1,1,1,1,1,1,1,1])
    image_names = ['main_image', 'other_image_1', 'other_image_2', 'other_image_3', 'other_image_4', 'other_image_5', 'other_image_6', 'other_image_7', 'other_image_8', 'swatch_image']
    
    with st.expander('Get links', icon=':material/link:'):
        links_area = st.container()

    with st.expander('Copy images from an old flat file', expanded=False, icon=":material/perm_media:"):
        clone_area = st.container()

    progress_bar, progress = st.progress(0.0), 0.0

    dictionary = gc.pull_dictionary()
    products = sorted(dictionary['collection'].unique().tolist())

    def sanitize_products(product: str):
        result = product.replace(' ','_').replace('/','_').replace('\\','_').lower()
        while '__' in result:
            result = result.replace('__','_')
        return result


    def create_links(source = target):
        if source == 'imagekit':
            files = list_files()
        else:
            files = list_files_gcs()
        if files:
            links = pd.DataFrame(files[1:], columns=files[0])
            dictionary_links = dictionary[['sku','collection','size','color']].drop_duplicates().copy()
            dictionary_links[['collection','size','color']] = dictionary_links[['collection','size','color']].map(sanitize_products)
            sku_links = pd.merge(links, dictionary_links, how = 'left', on = ['collection','size','color'])
            sku_links = sku_links[['sku','link', 'position']]
            skus = sku_links['sku'].unique()
            ordered_links = [pd.DataFrame(columns=image_names)]
            for sku in skus:
                link_data = sku_links[sku_links['sku'] == sku]
                link_data = link_data.pivot(index='sku',columns='position', values='link')
                ordered_links.append(link_data)
            ordered_links = pd.concat(ordered_links).reset_index().rename(columns={'index':'sku'})
            result_links = pd.merge(ordered_links, dictionary[['sku','collection','size','color']], how='left', on='sku')

            links_area.dataframe(result_links, hide_index=True)


    links_area.button('Get links', on_click=create_links, disabled=False, icon=':material/link:')


    def push_images(img_bytes, name, product, color, sizes, original_name, destination = target):
        """
        Pushes a single image to multiple folders based on size.
        This function is designed to be run in a separate thread and is pure.
        Returns a tuple containing the image name and a list of folders that failed to upload.
        """

        folders = [f'{product}/{color}/{size}' for size in sizes]
        failed_reasons = []
        for folder in folders:
            if destination == 'imagekit':
                tags = [product, color] + sizes
                result = upload_image(image_path=img_bytes, file_name=name, tags=tags, folder=folder)
            else:
                tags = {'product': product, 'color': color, 'sizes': sizes}
                result = upload_image_to_gcs(image_path=img_bytes, file_name=name, tags=tags, folder=folder)
            if result and result.startswith('ERROR:'):
                # Extract the size from the folder path for the error message
                failed_reasons.append(f'Path: {folder}, image: {original_name}, {result}')
        return (name, failed_reasons, folders)


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
        select_all_colors = selector_area.checkbox("Select all")

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
    image_areas = [img1_area,img2_area,img3_area,img4_area,img5_area,img6_area,img7_area,img8_area,img9_area,img_swtch_area]

    # Upload new images
    if st.session_state.selected_product and st.session_state.selected_colors and st.session_state.selected_sizes:
        files = [position.file_uploader(label=fr"{str(i)}\. {name}", type=ACCEPTED_FILE_TYPES) for i, (position, name) in enumerate(list(zip(image_positions, image_names)), start=1)]
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
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = []
                    for file, name in zip(files, image_names):
                        if file:
                            # Read file and encode it in the main thread
                            img_obj = file.read()
                            img_bytes = base64.b64encode(img_obj)
                            # Schedule the pure function to run with all data passed as arguments
                            for color in colors:
                                futures.append(executor.submit(push_images, img_bytes, f'{name}.jpg', product, color, selected_sizes, file.name))
                    
                    # Process results as they complete
                    for future in concurrent.futures.as_completed(futures):
                        image_name, failed_reasond, folders = future.result()
                        progress += 1/(len(futures))
                        progress_bar.progress(progress, text="Please wait, uploading images")
                        if failed_reasond:
                            failed_uploads.append({'image': image_name, 'reason': failed_reasond})
                        
                    progress_bar.progress(1.0, text="All done")

                if not failed_uploads:
                    st.success('All files pushed successfully!')
                else:
                    st.error('Some images failed to upload. Please see details below:')
                    for failure in failed_uploads:
                        st.write(f"Image: **{failure['image']}** failed: `{', '.join(failure['reason'])}`")

    # link extraction section
    def extract_links_for_cloning(flat_file_obj):
        result = []

        try:
            header_file = pd.read_excel(flat_file_obj, sheet_name='Template', skiprows=4, nrows=1)
            columns = [x for x in header_file.columns if any(['contribution_sku' in x, 'product_image_locator' in x])]
            flat_file = pd.read_excel(flat_file_obj, sheet_name='Template', skiprows=4, usecols=columns)
            flat_file = flat_file.drop(0)
            image_cols = [x for x in columns if 'sku' not in x]
            flat_file = flat_file.rename(columns=dict(zip(image_cols, image_names)))
            sku_col = [x for x in flat_file.columns if 'sku' in x][0]
            flat_file = flat_file.rename(columns={sku_col:'sku'})

            main_image_col = 'main_image'
            flat_file = flat_file.dropna(subset = main_image_col)
            flat_file_skus = flat_file['sku'].unique()
            for ffs in flat_file_skus:
                row = {}
                sku_flat_file = flat_file[flat_file['sku']==ffs]
                row['sku'] = ffs
                for image_col in image_names:
                    row[image_col] = sku_flat_file.loc[:,image_col].values[0]
                try:
                    row['product'] = dictionary[dictionary['sku']==ffs]['collection'].values[0]
                    row['size'] = dictionary[dictionary['sku']==ffs]['size'].values[0]
                    row['color'] = dictionary[dictionary['sku']==ffs]['color'].values[0]
                    result.append(row)
                except:
                    pass
        except Exception as e:
            st.warning(f'Please upload a valid flat file template: {e}')

        return result


    clone_file_button = clone_area.file_uploader(label='Upload flat file', type=['xls', 'xlsx', 'xlsm', 'xlsb'])

    if clone_file_button and not clone_file_button.file_id in st.session_state:
        st.session_state[clone_file_button.file_id] = True
        extracted_links = extract_links_for_cloning(clone_file_button)
        clone_links = {}
        for extracted_link in extracted_links:
            for position in image_names:
                if not extracted_link[position] is nan:
                    if not extracted_link[position] in clone_links:
                        clone_links[extracted_link[position]] = {}
                        clone_links[extracted_link[position]]['product'] = set([sanitize_products(extracted_link['product'])])
                        clone_links[extracted_link[position]]['colors'] = set([sanitize_products(extracted_link['color'])])
                        clone_links[extracted_link[position]]['sizes'] = set([sanitize_products(extracted_link['size'])])
                        clone_links[extracted_link[position]]['positions'] = set([position])
                    else:
                        clone_links[extracted_link[position]]['colors'].add(sanitize_products(extracted_link['color']))
                        clone_links[extracted_link[position]]['sizes'].add(sanitize_products(extracted_link['size']))
                        clone_links[extracted_link[position]]['positions'].add(position)
        failed_clones = []
        progress_bar.progress(0.0)
        progress = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            clone_futures = []
            for clone_link in clone_links:
                upload_product = list(clone_links[clone_link]['product'])[0]
                upload_colors = list(clone_links[clone_link]['colors'])
                upload_sizes = list(clone_links[clone_link]['sizes'])
                upload_positions = list(clone_links[clone_link]['positions'])
                for upload_color in upload_colors:
                    for upload_position in upload_positions:
                        clone_futures.append(executor.submit(push_images, clone_link, f'{upload_position}.jpg', upload_product, upload_color, upload_sizes, clone_link))

            for clone_future in concurrent.futures.as_completed(clone_futures):
                image_name, failed_reasons, folders = clone_future.result()
                st.toast(f'Successfully cloned `{", ".join(folders)}`')
                progress += 1/len(clone_futures)
                progress_bar.progress(progress, text='Please wait, cloning images...')

                if failed_reasons:
                    failed_clones.append({'image': image_name, 'reason': failed_reasons})
            progress_bar.progress(1.0, text='All done')

            if not failed_clones:
                st.success('All images cloned successfully!', icon=":material/celebration:")
            else:
                st.error('Some images failed to clone. Please see details below:', icon=":material/error:")
                for failure in failed_clones:
                    st.write(f"Image: **{failure['image']}** failed: `{', '.join(failure['reason'])}`")

        st.balloons()


else:
    st.warning('Only Amazon team has access to this tool.', icon="🔥")