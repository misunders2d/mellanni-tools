import os, html
from dotenv import load_dotenv
load_dotenv()

from typing import Final

from openai import OpenAI, NotFoundError # future development

from streamlit import secrets

from numpy import dot, array
from numpy.linalg import norm
import pandas as pd

from modules import gcloud_modules as gd

OPENAI_KEY: Final = secrets['AI_KEY_EMBEDDING']
if not OPENAI_KEY:
    raise BaseException('No openai key found')
EMB_MODEL: str = "text-embedding-3-small"
EMB_ROW_LIMIT: int = 1000
THRESH = 0.3
N_LABELS = 1
COMPLAINTS_FILE_ID = '1tMMJ6_3qe5ickYtoHYp0M-DfV5ffZKV1'

client = OpenAI(api_key=OPENAI_KEY)

def download_labels(file_id = COMPLAINTS_FILE_ID):
    labels = pd.read_excel(gd.gdownload(file_id))
    return labels

def get_embedding(text):
    """Returns an embedding or embeddings array for a given string or list of strings using OpenAI's embedding endpoint"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def cosine_similarity(a, b):
    return dot(a, b) / (norm(a) * norm(b))

def split_df(df: pd.DataFrame, num_rows: int) -> list[pd.DataFrame]:
    """
    Splits a given dataframe into chunks of specified number of rows, and puts the chunks into a list for further use.
    """
    if len(df) > num_rows:
        df_list = []
        for i in range(0,len(df),num_rows):
            temp_df = df.iloc[i:i+num_rows]
            df_list.append(temp_df)
    else:
        df_list = [df]
    return df_list

def get_embedding_df(df: pd.DataFrame, df_col: str) -> pd.DataFrame:
    if len(df) == 0:
        return None
    clean_df = df.copy()
    clean_df = clean_df.dropna(subset = df_col)
    clean_df = clean_df[clean_df[df_col] != 'nan']
    if len(clean_df) == 0:
        return df
    result = pd.DataFrame()
    if len(clean_df) > EMB_ROW_LIMIT:
        df_list = split_df(clean_df, EMB_ROW_LIMIT)
    else:
        df_list = [clean_df]
    for chunk in df_list:
        chunk.loc[:,df_col] = chunk.loc[:,df_col].astype(str).apply(html.unescape)
        texts = chunk[df_col].values.tolist()
        response = client.embeddings.create(
            input=texts,
            model=EMB_MODEL)
        emb = pd.DataFrame(response.data)[0].apply(lambda x: x[1])
        chunk.loc[:,'emb'] = emb.values
        result = pd.concat([result,chunk], axis = 0)
    return result

def clusterize_texts(df: pd.DataFrame, df_col: str, num_clusters: int = 10):
    from sklearn.cluster import KMeans
    embeddings = array(df[df_col].values.tolist())
    kmeans = KMeans(n_clusters=num_clusters)
    kmeans.fit(embeddings)
    labels = kmeans.labels_
    df['cluster'] = labels
    return df
    
def get_top_labels(row, n_labels):
    top_labels = row[row>THRESH].nlargest(n_labels).index.tolist()
    return top_labels

def assign_top_labels(df: pd.DataFrame, labels: pd.DataFrame,labels_col: str):
    similarity_columns = labels[labels_col].tolist()
    df['top reasons'] = df[similarity_columns].apply(get_top_labels, n_labels=N_LABELS, axis=1)
    for sim_col in similarity_columns:
        del df[sim_col]
    return df

def measure_label_relevance(
        df: pd.DataFrame,
        emb_col: str,
        labels: pd.DataFrame,
        labels_col: str
        ) -> pd.DataFrame:
    labels = get_embedding_df(labels, labels_col)
    for label in labels[labels_col].values.tolist():
        print(f'Matching "{label}" to dataset')
        label_emb = labels[labels[labels_col] == label]['emb'].values[0]
        df[label] = df[emb_col].map(lambda x: cosine_similarity(x, label_emb))
    return df