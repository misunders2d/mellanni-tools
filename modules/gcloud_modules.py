import streamlit as st
import pandas as pd
import gdown
from io import BytesIO
from google.cloud import bigquery
from google.oauth2 import service_account


def gdownload(file_id):
    buf = BytesIO()
    _ = gdown.download(id = file_id, output = buf)
    buf.seek(0)
    return buf

def gcloud_connect():
    key_path = service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'])
    client = bigquery.Client(credentials = key_path)
    return client

def list_projects():
    client = gcloud_connect()
    projects = [x.project_id for x in client.list_projects()]
    sections = [x.dataset_id for x in client.list_datasets()]
    table_list = {section:[x.table_id for x in client.list_tables(section)] for section in sections}
    client.close()
    return table_list

def pull_dictionary(combine:bool = False, market: str = 'US', full: bool = False, cols = None):
    if not full:
        columns = 'sku,asin,fnsku,upc,collection,sub_collection,size,color,short_title'
    elif not cols:
        columns = '*'
    elif cols:
        columns = cols
    dicts_dict = {
        'US':'`auxillary_development.dictionary`',
        'CA':'`auxillary_development.dictionary_ca`',
        'EU':'`auxillary_development.dictionary_eu`',
        'UK':'`auxillary_development.dictionary_uk`',
    }
    query = f'SELECT {columns} FROM {dicts_dict[market]}'
    sql_us = f'''SELECT {columns} FROM `auxillary_development.dictionary`'''
    sql_ca = f'''SELECT {columns} FROM `auxillary_development.dictionary_ca`'''
    sql_eu = f'''SELECT {columns} FROM `auxillary_development.dictionary_eu`'''
    sql_uk = f'''SELECT {columns} FROM `auxillary_development.dictionary_uk`'''

    with gcloud_connect() as client:
        if combine:
            dictionary_us_job = client.query(sql_us)
            dictionary_ca_job = client.query(sql_ca)
            dictionary_eu_job = client.query(sql_eu)
            dictionary_uk_job = client.query(sql_uk)
        else:
            dictionary = client.query(query).to_dataframe()
    if combine:
        dictionary_us = dictionary_us_job.to_dataframe()
        dictionary_ca = dictionary_ca_job.to_dataframe()
        dictionary_eu = dictionary_eu_job.to_dataframe()
        dictionary_uk = dictionary_uk_job.to_dataframe()
        dictionary = pd.concat([dictionary_us, dictionary_eu, dictionary_uk, dictionary_ca])
    dictionary = dictionary[~dictionary['fnsku'].isin(['bundle','none','FBM'])]
    dictionary['collection'] = dictionary['collection'].str.replace('1800','Iconic')
    dictionary['sub_collection'] = dictionary['sub_collection'].str.replace('1800','Iconic')
    return dictionary
    
def gcloud_daterange(client,
                     report = 'auxillary_development',
                     table = 'business_report',
                     start = None,
                     end = None,
                     columns = '*'):
    if isinstance(columns, list):
        cols = '`'+'`,`'.join(columns)+'`'
    else:
        cols = columns
    if any([start is None, end is None]):
        query = f'''
        SELECT {cols}
        FROM `{report}.{table}`'''
    else:
        query = f'''
        SELECT {cols}
        FROM `{report}.{table}`
        WHERE date >= "{start}"
        AND date <= "{end}"'''
    query_job = client.query(query)  # Make an API request.
    data = query_job.result().to_dataframe()
    client.close()
    return data

def get_last_date(client,report = 'reports',table = 'business_report'):
    date_cols = {
        'all_listing_report': 'date',
        'all_orders': 'purchase_date',
        'fba_inventory': 'date',
        'fba_returns': 'return_date',
        'fee_preview': 'date',
        'inventory': 'Date',
        'promotions': 'shipment_date',
        'storage_fee': 'date',
        'business_report': 'date'
        }
    column = date_cols[table]
    query = f"""
        SELECT {column}
        FROM `{report}.{table}`
        ORDER BY `{column}` DESC
        LIMIT 1
    """
    query_job = client.query(query)  # Make an API request.
    date = query_job.result().to_dataframe().values[0][0] #get results from query
    try:
        date = date.strftime('%Y-%m-%d')
    except:
        pass
    return date