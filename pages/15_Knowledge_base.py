import streamlit as st
from typing import Final
from openai import OpenAI, NotFoundError
from openai.types.beta.thread import Thread

from pinecone import Pinecone, ServerlessSpec
import uuid
from datetime import date


OPENAI_KEY: Final = st.secrets['KNOWLEDGE_BASE_AI_KEY']
PINECONE_API_KEY=st.secrets['PINECONE_API_KEY']

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index('knowledge-db')
NAMESPACE = 'db'

client = OpenAI(api_key = OPENAI_KEY)

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def add_record(problem, solution):
    text = '\n\n'.join((problem,solution))
    embedding = get_embedding(text)
    vectors = [
        {
            'id':str(uuid.uuid4()),
            'values':embedding,
            'metadata':{
                'problem':problem,
                'solution':solution,
                'date_created':str(date.today()),
                'date_modified':str(date.today())
                }
            }
        ]
    result = index.upsert(vectors = vectors, namespace = NAMESPACE)    
    return result

def delete_record_from_vector(key: str):
    index.delete(ids=[key], namespace=NAMESPACE)
    
def modify_record_vector(key: str, text: tuple):
    current_record = index.fetch(ids = [key], namespace = NAMESPACE)
    problem, solution = text
    embedding = get_embedding('\n\n'.join(text))
    index.update(
        id=key,
        values=embedding,
        set_metadata={
            "problem": problem, "solution": solution,
            'date_created':current_record.vectors[key]['metadata']['date_created'],
            'date_modified':str(date.today())
            },
            namespace=NAMESPACE
        )

def vector_search(query_str: str):
    query_emb = get_embedding(query_str)
    results = index.query(
        namespace=NAMESPACE,
        vector=query_emb,
        top_k=5,
        include_values=False,
        include_metadata=True
    )
    return results

def get_response(query, search_results):
    pre_prompt = f'''
                Below is the database search for my question "{query}".
                Please summarize and structure the search to best answer my question. If there is already a structure in the search - keep it reasonably intact.
                Please drop irrelevant results from your summary, but make sure to keep all links, file references and tool mentions.
                If there is a specific answer to my question in the search results - please answer it first, and then summarize the rest.
                If there is not enough information in search results to answer user's question - let the user know about it and try to answer with your own knowledge.
                Try to answer the user in the language which he used to ask the question, if possible.
                Make sure to include the "created" date and also "modified" date if it's different from the date of creation.
                '''
    response = client.chat.completions.create(
        messages = [
            {'role':'user','content':pre_prompt},
            {'role':'user','content':search_results}
            ],
        model = 'gpt-4o-mini',
        stream = True
    )
    return response


##################################### PAGE CONFIG #######################################
st.set_page_config(page_title = 'Mellanni knowledge base', page_icon = 'media/logo.ico',layout="wide",initial_sidebar_state='collapsed')

st.subheader('Mellanni Amazon knowledge database')
st.write("Tips and tricks on resolving non-ordinary Amazon-related issues.\nAsk a question in any language and see if there's any useful solution.\nIf not - please contact sergey@mellanni.com")

from login import login_st
if login_st():

    st.session_state.query = st.text_input('What is your question?')
    prefix_container = st.empty()
    summary_container = st.container(height = 500)
    mid_section = st.empty()
    raw_container = st.container(height = 400)

    if prefix_container.button('Submit'):
        # prefix_container.write(f'Your question: {st.session_state.query}')
        prefix_container.write(f"""Here's the AI summary for "{st.session_state.query}":""")
        vector_results = vector_search(st.session_state.query)
        # st.write(results)
        # st.write(type(results))

        search_results = '\n\n'.join(
            [
                f"""Problem: {x['metadata']['problem']}
                \nsolution: {x['metadata']['solution']}
                \nDate created: {x['metadata']['date_created']}
                \nDate modified: {x['metadata']['date_modified']}"""\
                for x in vector_results.matches
            ]
        )

        response = get_response(st.session_state.query, search_results)
        summary_container.write_stream(response)

        mid_section.write(f"Here's the most relevant raw results:")

        for result in vector_results.matches:
            problem = result.metadata['problem']
            solution = result.metadata['solution']
            relevance = result['score']
            dates = f"created on {result.metadata['date_created']}, modified on {result.metadata['date_modified']}"
            raw_container.markdown(f"Problem: {problem} (relevance score is {relevance})")
            raw_container.markdown(f"Solution: {solution}\n")
            raw_container.markdown(dates)
            raw_container.markdown(f'DB key: {result.id}')
            raw_container.write('--------------------')
