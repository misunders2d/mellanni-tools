import streamlit as st
import pandas as pd
import pandas_gbq
import datetime
from numpy import nan
import re, time
from modules import formatting as ff
# from modules import gcloud_modules as gc
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title = 'SKU changelog', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')

import login_google
st.session_state['login'] = login_google.login()
user_email = st.session_state['login'][1]

markets_access: dict = {
    'ruslan@mellanni.com':['CA','US'],
    'vova@mellanni.com':['CA','US'],
    'sergey@mellanni.com':['CA','US','UK','Target','Shopify'],
    '2djohar@gmail.com':['CA','US','UK','Target','Shopify'],
    'oleksandr@mellanni.com':['US'],
    'bohdan@mellanni.com':['US'],
    'vitalii@mellanni.com':['US','CA'],
    'reymond@mellanni.com':['US'],
    'olha@mellanni.com':['UK','DE','FR','ES','IT'],
    'natalie@mellanni.com':['WM', 'Target','Shopify'],
    'andreia@mellanni.com':['WM', 'Target','Shopify'],
}


if st.session_state['login'][0] and user_email in markets_access:

# user_email = 'sergey@mellanni.com'
# if True:

    GC_CREDENTIALS = service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'])
    client = bigquery.Client(credentials=GC_CREDENTIALS)
    NUM_DAYS = 60

    change_types = [
        'Price increase', 'Price decrease', 'Main image update', 'Secondary images update',
        'Title change','Bulletpoints change', 'Search terms/backend change',
        'Negative review removal', 'Coupon activated','Coupon deactivated', 'Discount (promo)',
        'EBC created', 'EBC changed', 'Blocked/Suspended','Unblocked/Unsuspended',
        'Video added/Updated','PPC budget increased','PPC budget decreased',
        'Removed from parent','Added to parent','Rebate started','Rebate finished','LD','SMPC'
        ]
    markets_match:dict = {
        'dictionaries':{
            'US':'`auxillary_development.dictionary`',
            'CA':'`auxillary_development.dictionary_ca`',
            # 'EU':'`auxillary_development.dictionary_eu`',

            'DE':'`auxillary_development.dictionary_eu`',
            'FR':'`auxillary_development.dictionary_eu`',
            'ES':'`auxillary_development.dictionary_eu`',
            'IT':'`auxillary_development.dictionary_eu`',

            'UK':'`auxillary_development.dictionary_uk`',
            'WM':'`auxillary_development.dictionary`',
            'Target':'`auxillary_development.dictionary`',
            'Shopify':'`auxillary_development.dictionary`',
        },
        'changelogs':{
            'US':'`auxillary_development.sku_changelog`',
            'CA':'`auxillary_development.sku_changelog_ca`',
            # 'EU':'`auxillary_development.sku_changelog_eu`',

            'DE':'`auxillary_development.sku_changelog_de`',
            'FR':'`auxillary_development.sku_changelog_fr`',
            'ES':'`auxillary_development.sku_changelog_es`',
            'IT':'`auxillary_development.sku_changelog_it`',

            'UK':'`auxillary_development.sku_changelog_uk`',
            'WM':'`auxillary_development.dictionary_wm`',
            'Target':'`auxillary_development.dictionary_tgt`',
            'Shopify':'`auxillary_development.dictionary_shp`',
        }
    }
    button_access = user_email in markets_access
    allowed_markets = [x for x in markets_match['dictionaries'].keys() if x in markets_access.get(user_email,[])]

    @st.cache_resource
    def pull_dictionary(
        marketplace:str = 'US'
        ) -> pd.DataFrame:
        columns = ', '.join(['sku','asin','collection','size','color'])
        dictionary_report =  markets_match['dictionaries'].get(marketplace)
        query = f'SELECT {columns} FROM {dictionary_report}'
        if dictionary_report is not None:
            with bigquery.Client(credentials=GC_CREDENTIALS) as client:
                dictionary = client.query(query).result().to_dataframe()
        return dictionary

    # @st.cache_resource
    def pull_changes(
            marketplace:str = 'US',
            start:datetime.date = (pd.to_datetime('today')-pd.Timedelta(days = NUM_DAYS)).date(),
            end:datetime.date = pd.to_datetime('today').date()
            ) -> pd.DataFrame:
        columns = ', '.join(['date','sku','change_type','notes'])
        report = markets_match['changelogs'].get(marketplace)
        query = f'SELECT {columns} FROM {report} WHERE DATE(date) >= DATE("{start}") AND DATE(date) <= DATE("{end}")'
        if report is not None:
            try:
                with bigquery.Client(credentials=GC_CREDENTIALS) as client:
                    changes = client.query(query).result().to_dataframe()
            except:
                return pd.DataFrame(columns = ['date','sku','change_type', 'notes'])
        else:
            return pd.DataFrame(columns = ['date','sku','change_type','notes'])
        return changes

    # @st.cache_resource
    def summarize_changes(
        changes:pd.DataFrame
        ) -> pd.DataFrame:
        # changes['notes'] = changes['notes'].replace('',nan)
        pivot = changes.pivot_table(
            values=['sku', 'change_type', 'date', 'notes'],
            index=['collection'],
            aggfunc={
                'sku':lambda x: len(x.unique()),
                'change_type': lambda x: ', '.join(x.unique().tolist()),
                'date':lambda x: min(x)+' - '+max(x),
                'notes': lambda x: ', '.join(x.unique().tolist())
                }
        ).reset_index()
        pivot = pivot.rename(columns = {'date':'date range','sku':'# of skus affected'})
        return pivot

    def generate_skus(
            collections:list,
            sizes:list,
            colors:list,
            dictionary:pd.DataFrame
            ) -> None:
        skus = dictionary[dictionary['collection'].isin(collections)]['sku'].unique().tolist()
        if len(sizes) > 0:
            skus = dictionary[
                (dictionary['collection'].isin(collections))
                & (dictionary['size'].isin(sizes))
                ]['sku'].unique().tolist()
        if len(colors) > 0:
            skus = dictionary[
                (dictionary['collection'].isin(collections))
                & (dictionary['size'].isin(sizes))
                & (dictionary['color'].isin(colors))
                ]['sku'].unique().tolist()
        return skus

    def generate_collections_from_skus(
            skus: list,
            dictionary: pd.DataFrame
            ) -> list:
        collections = dictionary[dictionary['sku'].isin(skus)]['collection'].unique().tolist()
        return collections

    def add_changes(
            skus:list,
            change_type:str,
            notes:str,
            marketplace:str = 'US',
            date:datetime.date = (pd.to_datetime('today')).date()
            ) -> None:
        changes_df = pd.DataFrame(list(zip(
            [date for x in range(len(skus))],
            skus,
            [change_type for x in range(len(skus))],
            [notes for x in range(len(skus))])), columns = ['date','sku','change_type','notes'])
        target_report = markets_match['changelogs'].get(marketplace).replace('`','')
        columns = [x for x in changes_df.columns]
        for c in columns:
            changes_df[c] = changes_df[c].astype(str)
        pandas_gbq.to_gbq(
            project_id="mellanni-project-da",
            dataframe = changes_df,
            destination_table=target_report,
            if_exists='append',
            credentials=GC_CREDENTIALS,
            progress_bar=False
            )
        # changes_df.to_gbq(target_report, chunksize=1000, if_exists='replace', project_id = 'mellanni-project-da', progress_bar=True)
        st.success('Changes saved to BigQuery')
        time.sleep(2)
        st.rerun()
        return None

    def hide_df():
        st.session_state.df_height = 1
        return None


    # global change_types
    markets_row = st.container()
    selectors_row = st.container()
    summary_area = st.container()
    df_area = st.container()
    
    marketplace_col, date_col, change_type_col, button_col = markets_row.columns([3,1,2,1])
    marketplace = marketplace_col.radio('Select marketplace', allowed_markets, horizontal=True)

    if marketplace == 'Shopify':
        change_types.extend(['MSRP set as Sale Price + discount coupon to standard','Prices back to Standard from MSRP, coupon off'])
    elif marketplace == 'WM':
        change_types.extend(['Spec file upload','Unpublished - OOS','Published - Back in Stock'])
    elif marketplace in ('UK', 'DE','FR','ES','IT'):
        change_types.extend(['TOP DEAL STARTED', 'TOP DEAL ENDED', 'BEST DEAL STARTED', 'BEST DEAL ENDED', 'OUTLET DEAL STARTED', 'OUTLET DEAL ENDED',
                             'PED started','PED ended','SALE started','SALE ended'])
    change_types = sorted(change_types)
    change_types.append('Other, please specify in notes')

    change_type = change_type_col.selectbox('Select a change',options = change_types, index = change_types.index(change_types[-1]))
    notes = change_type_col.text_input('Add notes, if necessary')
    change_date = date_col.date_input('Date of the change', value = 'today')
    add_button = button_col.button('Add changes', type = 'primary', disabled = not button_access)#, on_click=hide_df)

    st.session_state.changes = pull_changes(marketplace=marketplace)
    st.session_state.dictionary = pull_dictionary(marketplace=marketplace)
    st.session_state.changelog = pd.merge(st.session_state.changes, st.session_state.dictionary, how = 'left', on = 'sku')
    st.session_state.pivot = summarize_changes(st.session_state.changelog)
    result = ff.prepare_for_export([st.session_state.changelog], ['changes'])
    st.download_button('Download changes',result, file_name = 'sku_changelog.xlsx')

    collection_list, size_list, color_list, sku_list = selectors_row.columns([2,1,1,2])
    collections_filtered = sorted(st.session_state.dictionary['collection'].sort_values().unique().tolist())
    st.session_state.collections = collection_list.multiselect('Collection', collections_filtered)

    sizes_filtered = sorted(st.session_state.dictionary[st.session_state.dictionary['collection'].isin(st.session_state.collections)]['size'].sort_values().unique())
    st.session_state.sizes = size_list.multiselect('Size',sizes_filtered)
    
    colors_filtered = st.session_state.dictionary[
        (st.session_state.dictionary['collection'].isin(st.session_state.collections))
        & (st.session_state.dictionary['size'].isin(st.session_state.sizes))
        ]['color'].sort_values().unique()
    st.session_state.colors = color_list.multiselect('Color',colors_filtered)

    skus_filtered = generate_skus(st.session_state.collections, st.session_state.sizes, st.session_state.colors, st.session_state.dictionary)

    st.session_state.skus = sku_list.text_area(f'SKUs ({len(skus_filtered)} selected)', value = ', '.join(skus_filtered))
    st.session_state.skus = [x.strip() for x in re.split('\n|,|;|\t', st.session_state.skus)]
    collections_from_skus = generate_collections_from_skus(st.session_state.skus, st.session_state.dictionary)

    if 'df_height' not in st.session_state:
        summary_area.write(f'Summary of latest changes for the past {NUM_DAYS} days')
        df_area.dataframe(st.session_state.pivot, use_container_width=True, hide_index=True)
    collections_str = '\n'.join(collections_from_skus)
    warning_text = f'''You are about to commit the following changes to {marketplace} changelog:
Change: {change_type},
Notes: {notes},
Change date: {change_date}
{len(st.session_state.skus)} skus impacted, including the following collections: {collections_str}
'''

    if add_button:
        st.session_state.warning = True
        st.text_area('Warning', value=warning_text, disabled = True, height = 400)
    if 'warning' in st.session_state:
        if st.button('Confirm'):
            add_changes(st.session_state.skus, change_type, notes, marketplace, change_date)
            # st.session_state.df = add_changes(st.session_state.skus, change_type, notes, marketplace, change_date)
    # if 'df' in st.session_state:
    #     st.dataframe(st.session_state.df)

    # st.write(st.session_state.sizes)
    # st.write(st.session_state.colors)
    # st.write(st.session_state.skus)

# if __name__ == '__main__':
#     main()


# NEED TO CREATE A CHANGELOG FOR OTHER MARKETPLACES
# - Adding skus/collections to changelog
# - Removing skus/collections from changes
# - Showing latest changes