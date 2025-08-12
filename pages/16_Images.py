import re
import streamlit as st
import pandas as pd
import base64
from typing import Literal
from numpy import nan
from modules.image_modules import (
    upload_image, list_files, upload_image_to_gcs,
    list_files_gcs, update_version_gcs,
    headers
    )
from modules import gcloud_modules as gc
from modules.sc_modules import push_images_to_amazon, get_listing_details, extract_sku_images
import concurrent.futures

st.set_page_config(layout='wide', initial_sidebar_state='collapsed')

ACCEPTED_FILE_TYPES = '.jpg'
MAX_WORKERS=10

from login import login_st
if login_st() and st.user.email in ('sergey@mellanni.com','ruslan@mellanni.com','bohdan@mellanni.com','vitalii@mellanni.com', '2djohar@gmail.com'):

    image_names = ['main_image', 'other_image_1', 'other_image_2', 'other_image_3', 'other_image_4', 'other_image_5', 'other_image_6', 'other_image_7', 'other_image_8', 'swatch_image']
    dictionary = gc.pull_dictionary()

    with st.expander('Images on Amazon', expanded=False, icon=":material/image:"):
        amz1_area, amz2_area, amz3_area, amz4_area, amz5_area, amz6_area, amz7_area, amz8_area, amz9_area, amz_swtch_area = st.columns([1,1,1,1,1,1,1,1,1,1])
        get_images_area, view_amaon_area, _ = st.columns([3, 1, 3])

        amz_positions = dict(zip(image_names, [amz1_area, amz2_area, amz3_area, amz4_area, amz5_area, amz6_area, amz7_area, amz8_area, amz9_area, amz_swtch_area]))
        if get_images_area.button('Get ASIN images', icon=':material/refresh:', type='tertiary'):
            if all(['selected_product' in st.session_state, 'selected_colors' in st.session_state, 'selected_sizes' in st.session_state]) and all(
                [len(st.session_state.selected_colors) == 1, len(st.session_state.selected_sizes) == 1]):

                try:
                    selected_product = st.session_state.selected_product or ""
                    selected_color = st.session_state.selected_colors[0] if st.session_state.selected_colors and st.session_state.selected_colors[0] is not None else ""
                    selected_size = st.session_state.selected_sizes[0] if st.session_state.selected_sizes and st.session_state.selected_sizes[0] is not None else ""
                    sku, asin = dictionary[
                        (dictionary['collection']==selected_product)
                        &
                        (dictionary['color']==selected_color)
                        &
                        (dictionary['size']==selected_size)
                        ][['sku','asin']].values[0]
                    sku_details = extract_sku_images(get_listing_details(sku, include=['attributes']))

                    for position, link in sku_details.items():

                        if position in amz_positions:
                            amz_positions[position].image(link, caption=position)

                    # Insert a link to the Amazon ASIN page
                    if asin:
                        amazon_url = f"https://www.amazon.com/dp/{asin}"
                        view_amaon_area.markdown(f"[View on Amazon]({amazon_url})", unsafe_allow_html=True)
                except:
                    st.warning('Please select a product, color and size first.')

            else:
                st.warning('Please select a product, color and size first.')

    with st.expander('Upload images', expanded=True, icon=":material/image_arrow_up:"):
        product_area, color_area, selector_area, size_area, storage_selector_area = st.columns([6, 6, 2, 6, 2])
        img1_input, img2_input, img3_input, img4_input, img5_input, img6_input, img7_input, img8_input, img9_input, swtch_input = st.columns([1,1,1,1,1,1,1,1,1,1])
        img1_area, img2_area, img3_area, img4_area, img5_area, img6_area, img7_area, img8_area, img9_area, img_swtch_area = st.columns([1,1,1,1,1,1,1,1,1,1])
        
    target: str = storage_selector_area.radio(
        'Select storage', options=['imagekit', 'gcs'], index=1, horizontal=False, disabled=True,
        help='We have two options for image storage, but regardless of the option the links are the same.'
        )
    
    with st.expander('Get links', icon=':material/link:'):
        links_area = st.container()

    with st.expander('Current images', icon=':material/image:', expanded=True):
        view_area = st.container()
        button_area = st.container()
        cache_button, push_button, _, _, _ = button_area.columns([1, 1, 1, 1, 1])
        versions_toggle = view_area.checkbox('Show versions', value=False, help='If you want to see the versions of the image, check this box.')

    with st.expander('Copy images from an old flat file', expanded=False, icon=":material/perm_media:"):
        clone_area = st.container()

    progress_bar, progress = st.progress(0.0), 0.0
    products = sorted(dictionary['collection'].unique().tolist())

    def sanitize_products(product: str):
        result = re.sub(r'[^\w]', '_', product).lower()
        while '__' in result:
            result = result.replace('__','_')
        if result.endswith('_'):
            result = result[:-1]
        return result

    def create_links(source = target):
        if not 'selected_product' in st.session_state or not st.session_state.selected_product:
            folder = None
        else:
            folder = sanitize_products(st.session_state.selected_product)
        if source == 'imagekit':
            files = list_files(folder=folder)
        else:
            files = list_files_gcs(folder=folder, versions=None, include_bytes=False)
        if files:
            files = [[x['product'],x['color'],x['size'],x['image'],x['position']] for x in files]
            links = pd.DataFrame(files, columns=headers)
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
            st.session_state.result_links = pd.merge(ordered_links, dictionary[['sku','collection','size','color']], how='left', on='sku')


    links_area.button('Get links', on_click=create_links, disabled=False, icon=':material/link:')

    if 'result_links' in st.session_state:
        links_area.dataframe(st.session_state.result_links, hide_index=True)

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
                    button_area.success('All files pushed successfully!')
                else:
                    button_area.error('Some images failed to upload. Please see details below:')
                    for failure in failed_uploads:
                        st.write(f"Image: **{failure['image']}** failed: `{', '.join(failure['reason'])}`")

    # link extraction section
    def extract_links_for_cloning(flat_file_obj):
        result = []

        try:
            header_file = pd.read_excel(flat_file_obj, sheet_name='Template', skiprows=4, nrows=1)
            columns = [x for x in header_file.columns if any(
                ['contribution_sku' in x, 'product_image_locator' in x]
                )]
            flat_file = pd.read_excel(flat_file_obj, sheet_name='Template', skiprows=4, usecols=columns)
            flat_file = flat_file.drop(0)
            image_cols = [x for x in columns if 'sku' not in x]
            flat_file = flat_file.rename(columns=dict(zip(image_cols, image_names)))
            sku_col = [x for x in flat_file.columns if 'sku' in x][0]
            flat_file = flat_file.rename(columns={sku_col:'sku'})
            dictionary_skus = dictionary['sku'].unique().tolist()

            # main_image_col = 'main_image'
            # flat_file = flat_file.dropna(subset = main_image_col)
            flat_file_skus = flat_file['sku'].unique()
            for ffs in flat_file_skus:
                if not ffs in dictionary_skus:
                    continue
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
        final = {}
        for r in result:
            if (r['product'], r['color'], r['size']) not in final:
                final.update({(r['product'], r['color'], r['size']): r})
        return [x for x in final.values()]

    clone_disable = False if st.user.email == "sergey@mellanni.com" else True
    clone_file_button = clone_area.file_uploader(
        label='Upload flat file',
        type=['xls', 'xlsx', 'xlsm', 'xlsb'],disabled=clone_disable,
        help='Please upload a flat file with images. The file should have a "Template" sheet with the following columns: "contribution_sku", "product_image_locator", and image names as columns.'
        )

    if clone_file_button and not clone_file_button.file_id in st.session_state:
        st.session_state[clone_file_button.file_id] = True
        extracted_links = extract_links_for_cloning(clone_file_button)
        clone_links = []
        for extracted_link in extracted_links:
            for position in image_names:
                if not extracted_link[position] is nan:
                    clone_links.append(
                        {
                            'link':extracted_link[position],
                            'position':position,
                            'product':extracted_link['product'],
                            'size':extracted_link['size'],
                            'color':extracted_link['color'],
                            }
                        )

        failed_clones = []
        progress_bar.progress(0.0)
        progress = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            clone_futures = []
            for clone_link in clone_links:
                upload_product = sanitize_products(clone_link['product'])
                upload_color = sanitize_products(clone_link['color'])
                upload_size = [sanitize_products(clone_link['size'])]
                upload_position = sanitize_products(clone_link['position'])
                # result = push_images(clone_link['link'],f'{upload_position}.jpg',upload_product,upload_color,upload_size, clone_link['link'])
                # print(result)
                clone_futures.append(
                    executor.submit(
                        push_images,
                        clone_link['link'],
                        f'{upload_position}.jpg',
                        upload_product,
                        upload_color,
                        upload_size, clone_link['link']
                        )
                    )

            for clone_future in concurrent.futures.as_completed(clone_futures):
                image_name, failed_reasons, folders = clone_future.result()
                st.toast(f'Cloning `{", ".join(folders)}`')
                progress += 1/len(clone_futures)
                progress_bar.progress(progress, text='Please wait, cloning images...')

                if failed_reasons:
                    failed_clones.append({'image': image_name, 'reason': failed_reasons})
            progress_bar.progress(1.0, text='All done')

            if not failed_clones:
                button_area.success('All images cloned successfully!', icon=":material/celebration:")
            else:
                button_area.error('Some images failed to clone. Please see details below:', icon=":material/error:")
                for failure in failed_clones:
                    st.write(f"Image: **{failure['image']}** failed: `{', '.join(failure['reason'])}`")

        st.balloons()

    def start_update_image(blob_name: str, blob_generation: str, action, position: str, image: str):
        start_push_images_to_amazon(action=action, position=position, image=image)
        update_image(blob_name, blob_generation, action)


    def update_image(blob_name: str, blob_generation: str, action) -> None:
        """Deletes a specific version of a blob in GCS."""
        result = update_version_gcs(blob_name, blob_generation, action)
        if result.startswith('ERROR:'):
            button_area.error(result)
        else:
            button_area.success(result)
            # st.cache_data.clear()

    def start_push_images_to_amazon(action: Literal['replace','delete'], position = None, image = None):
        if all(['selected_product' in st.session_state, 'selected_colors' in st.session_state, 'selected_sizes' in st.session_state]) and all(
            [len(st.session_state.selected_colors) == 1, len(st.session_state.selected_sizes) == 1]):

            selected_product = st.session_state.selected_product or ""
            selected_color = st.session_state.selected_colors[0] if st.session_state.selected_colors and st.session_state.selected_colors[0] is not None else ""
            selected_size = st.session_state.selected_sizes[0] if st.session_state.selected_sizes and st.session_state.selected_sizes[0] is not None else ""
            skus = dictionary[
                (dictionary['collection']==selected_product)
                &
                (dictionary['color']==selected_color)
                &
                (dictionary['size']==selected_size)
                ]['sku'].unique().tolist()
            
            if action == 'replace':
                images_to_push = {x['position']: x['image'] for x in blobs}
            else:
                images_to_push = {position: image}
                
            results = push_images_to_amazon(skus, images_to_push, action=action)
            button_area.warning('\n'.join(results), icon=":material/arrow_upward:")

    img1_view, img2_view, img3_view, img4_view, img5_view, img6_view, img7_view, img8_view, img9_view, img_swtch_view = view_area.columns([1,1,1,1,1,1,1,1,1,1])
    img_view_positions = dict(zip(image_names, [img1_view, img2_view, img3_view, img4_view, img5_view, img6_view, img7_view, img8_view, img9_view, img_swtch_view]))
    try:
        if all([
                'selected_product' in st.session_state, 'selected_colors' in st.session_state, 'selected_sizes' in st.session_state,
                ]
            ) and all([
                len(st.session_state.selected_colors) == 1, len(st.session_state.selected_sizes) == 1
                ]):
            selected_product = st.session_state.selected_product or ""
            selected_color = st.session_state.selected_colors[0] if st.session_state.selected_colors and st.session_state.selected_colors[0] is not None else ""
            selected_size = st.session_state.selected_sizes[0] if st.session_state.selected_sizes and st.session_state.selected_sizes[0] is not None else ""
            blobs = list_files_gcs(
                folder=f"{sanitize_products(selected_product)}/{sanitize_products(selected_color)}/{sanitize_products(selected_size)}",
                versions=versions_toggle,
                include_bytes=False
            )
            # view_area.write(blobs)
            if blobs:
                image_list = {}
                for image_name in image_names:
                    for blob in blobs:
                        name, img, img_bytes, updated, generation, position = blob['name'], blob['image'], blob['image_bytes'], blob['updated'], blob['generation'], blob['position']
                        if image_name in blob['position'] and image_name not in image_list:
                            image_list[image_name] = [{'name':name, 'image':img, 'image_bytes': img_bytes, 'updated':updated, 'generation':generation, 'position': position}]
                        elif image_name in blob['position'] and image_name in image_list:
                            image_list[image_name].append({'name':name, 'image':img, 'image_bytes': img_bytes, 'updated':updated, 'generation':generation, 'position': position})
                for img in image_list:
                    image_list[img] = sorted(image_list[img], key=lambda x: int(x['generation']), reverse=True)
                # st.write(image_list)
                for image_name in image_names:
                    if image_name in image_list:
                        for ver, object in enumerate(image_list[image_name]):
                            try:
                                img_view_positions[image_name].image(
                                    object['image'],
                                    caption=f'{image_name}, updated: {object['updated'].strftime("%Y-%m-%d %H:%M:%S")}, version: {object['generation']}'
                                    )
                                if ver == 0:
                                    # delete image from GCS and Amazon
                                    img_view_positions[image_name].button(
                                        'Delete Storage / Amazon',
                                        key=f'{object['generation']}_delete_completely',
                                        type='tertiary',
                                        icon=':material/delete_forever:',
                                        on_click=start_update_image,
                                        args=(object['name'], object['generation'], 'delete', object['position'], object['image'])
                                        )
                                    img_view_positions[image_name].link_button('Open image', object['image'], icon=':material/open_in_new:', type='tertiary')
                                elif ver > 0:
                                    # delete image from GCS only
                                    img_view_positions[image_name].button(
                                        'Delete version',
                                        key=f'{object['generation']}_remove',
                                        type='tertiary',
                                        icon=':material/delete_forever:',
                                        on_click=update_image,
                                        args=(object['name'], object['generation'], 'delete')
                                        )


                                    img_view_positions[image_name].button( 
                                        'Restore version',
                                        key=f'{object['generation']}_restore',
                                        type='tertiary',
                                        icon=':material/restore_from_trash:',
                                        on_click=update_image,
                                        args=(object['name'], object['generation'], 'restore')
                                    )
                            except Exception as e:
                                img_view_positions[image_name].error(f'Error loading image: {e}')
                                img_view_positions[image_name].button(
                                    'Delete version', key=f'{object['generation']}_delete_error', type='tertiary',
                                    on_click=start_update_image,args=(object['name'], object['generation'], 'delete', object['position'], object['image']))
            if not versions_toggle:
                push_button.button('Push to Amazon', icon=':material/arrow_upward:', help='Push main image to Amazon seller central.',
                    on_click=start_push_images_to_amazon,
                    args = ('replace',),
                    disabled=False, 
                    )
        cache_button.button('Clear cache', on_click=lambda: st.cache_data.clear(), disabled=False, icon=':material/clear_all:')
    except Exception as e:
        view_area.error(f'Error loading images: {e}')

else:
    st.warning('Only Amazon team has access to this tool.', icon="🔥")