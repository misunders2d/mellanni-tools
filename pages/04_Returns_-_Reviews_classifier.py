import streamlit as st
st.set_page_config(page_title = 'Returns and reviews analyzer', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')
from io import BytesIO
import pandas as pd
from matplotlib import pyplot as plt

from modules import gcloud_modules as gc
from modules import embed_modules as em
from modules import formatting as ff
COUNTRIES = ['DE','GB','ES','IT','FR','US']


st.subheader('Negative comments classifier')

# import login_google
# st.session_state['login'] = login_google.login()

# if st.session_state['login'][0]:
if True:
    # initialize dictionary and selectors
    date_to = pd.to_datetime('today').date()
    date_from = date_to - pd.Timedelta(days = 10)
    if not 'dictionary' in st.session_state:
        with st.spinner('Please wait, preparing data...'):
            st.session_state['dictionary'] = gc.pull_dictionary(cols = ['asin', 'collection', 'size', 'color'],combine = True)
            st.session_state['labels'] = em.download_labels()
    dictionary = st.session_state['dictionary']
    labels = st.session_state['labels']
    if not 'params' in st.session_state:
        st.session_state['params'] = {'collection':[], 'size':[], 'color':[]}
    params = st.session_state['params']

    def filter_dictionary(dictionary: pd.DataFrame = dictionary, **kwargs):
        df = dictionary.copy()
        if kwargs and len(filter_parameters:= [f'`{column}`.isin({value})' for column, value in kwargs.items() if value !=[]]) > 0:
            filter_query = ' & '.join([x for x in filter_parameters])
            filtered_dictionary = df.query(filter_query)
            return filtered_dictionary
        return df

    def summarize_returns(df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby('asin')['quantity'].agg("sum").reset_index().sort_values('quantity', ascending=False)

    filtered_dictionary = filter_dictionary(dictionary, **params)

    choice = st.radio('Switch between Returns comments and Negative Reviews classifier',['Returns','Reviews'], horizontal = True, disabled=True)
    chart_area, filters_area = st.columns([0.75, 0.25])
    country = filters_area.radio('Country', options = COUNTRIES, index = len(COUNTRIES)-1, horizontal=True, label_visibility='hidden')
    start = filters_area.date_input('From', date_from)
    end = filters_area.date_input('To', date_to)

    collection = filters_area.multiselect(
        label='Collection(s):',
        options=sorted(dictionary['collection'].unique()),
        placeholder='Select a collection',
        label_visibility='hidden'
        )
    if collection or collection == []:
        params['collection'] = collection
        filtered_dictionary = filter_dictionary(dictionary, **params)
    size = filters_area.multiselect('Size(s):', sorted(dictionary['size'].unique()), placeholder='Select a size', label_visibility='hidden')
    if size or size == []:
        params['size'] = size
        filtered_dictionary = filter_dictionary(dictionary, **params)
    color = filters_area.multiselect('Color(s):', sorted(dictionary['color'].unique()), placeholder='Select a color', label_visibility='hidden')
    if color or color == []:
        params['color'] = color
        filtered_dictionary = filter_dictionary(dictionary, **params)

    filtered_dictionary = filter_dictionary(dictionary, **params)
    asins = filtered_dictionary['asin'].unique().tolist()
    asins_str = ', '.join([f'"{asin}"' for asin in asins])


    if choice == 'Returns':
        query = f"""
                    SELECT return_date, asin, quantity, customer_comments
                    FROM `mellanni-project-da.reports.fba_returns`
                    WHERE asin IN ({asins_str})
                    AND
                    country_code = "{country}"
                    AND
                    DATE(return_date) BETWEEN DATE("{start}") AND DATE("{end}")
                """
        if st.button('Analyze returns'):
            with st.spinner(f'Please wait, pulling data from {country} for {len(asins)} variations...', _cache = True):
                with gc.gcloud_connect() as client:
                    st.session_state.returns = client.query(query).to_dataframe()
            if 'returns' in st.session_state and len(st.session_state.returns) > 0:
                with st.spinner(f'Please wait, analyzing {len(st.session_state.returns)} complaints'):
                    embedded_returns = em.get_embedding_df(st.session_state.returns, 'customer_comments')
                    label_relevances = em.measure_label_relevance(embedded_returns, 'emb', labels, 'Return reason')
                    reasons = em.assign_top_labels(label_relevances, labels, 'Return reason')
                    reasons['top reasons'] = reasons['top reasons'].apply(lambda x: x[0] if len(x)>0 else None)
                    reasons = pd.merge(reasons, labels, how = 'left', left_on = 'top reasons', right_on = 'Return reason')
                    del reasons['emb']
                    del reasons['Return reason']
                    del reasons['top reasons']
                    reasons['Label'] = reasons['Label'].fillna('Unknown')
                    summary = reasons.groupby('Label')['quantity'].agg('sum').reset_index().sort_values('quantity', ascending = False)
                    chart_area.bar_chart(data = summary, x = 'Label', y = 'quantity')
                    # labels_list = reasons['Label'].unique()
                    # filter_labels = st.multiselect('Select reason to filter:', labels_list)
                    # if filter_labels:
                    #     st.dataframe(reasons[reasons['Label'].isin(filter_labels)])
                    # else:
                    #     st.dataframe(reasons)
                    reasons = pd.merge(reasons, dictionary.drop_duplicates('asin')[['asin','collection','size','color']], how = 'left', on = 'asin')
                    st.dataframe(reasons)
            else:
                st.info('No complaints to analyze')
    elif choice == 'Reviews':
        query = f"""
                    SELECT date, asin, title, body, rating
                    FROM `mellanni-project-da.auxillary_development.reviews_{country.lower()}`
                    WHERE asin IN ({asins_str})
                    AND
                    DATE(date) BETWEEN DATE("{start}") AND DATE("{end}")
                    AND CAST(rating AS INTEGER) < 4
                """

        if st.button('Analyze reviews'):
            with st.spinner(f'Please wait, pulling data from {country} for {len(asins)} variations...', _cache = True):
                with gc.gcloud_connect() as client:
                    try:
                        st.session_state.reviews = client.query(query).to_dataframe()
                    except:
                        st.session_state.reviews = pd.DataFrame()
                    # chart_area.dataframe(st.session_state.reviews)
            if 'reviews' in st.session_state and len(st.session_state.reviews) > 0:
                with st.spinner(f'Please wait, analyzing {len(st.session_state.reviews)} reviews'):
                    review_temp = st.session_state.reviews.copy()
                    review_temp[['title','body']] = review_temp[['title','body']].astype(str)
                    review_temp['customer_comments'] = review_temp['title']+ '\n' +review_temp['body']
                    embedded_returns = em.get_embedding_df(review_temp, 'customer_comments')
                    label_relevances = em.measure_label_relevance(embedded_returns, 'emb', labels, 'Return reason')
                    reasons = em.assign_top_labels(label_relevances, labels, 'Return reason')
                    del reasons['emb']
                    del reasons['customer_comments']
                    reasons['top reasons'] = reasons['top reasons'].astype(str).replace('[]','[Unidentified]')
                    summary = reasons.groupby('top reasons')['rating'].agg(lambda x: len(x)).reset_index().sort_values('rating', ascending = False)
                    summary = summary.rename(columns = {'rating':'ratings'})
                    chart_area.bar_chart(data = summary, x = 'top reasons', y = 'ratings')
                    st.dataframe(reasons)
            else:
                st.info('No reviews to analyze')

