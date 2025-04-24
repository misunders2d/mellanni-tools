from openai import OpenAI
import streamlit as st
import time, os, re
import keepa
from modules.keepa_modules import get_product_details


st.set_page_config(page_title = 'Mellanni Tools App', page_icon = 'media/logo.ico',layout="wide")

KEEPA_KEY = os.getenv('KEEPA_KEY')
ASSISTANT_KEY = st.secrets['ASSISTANT_KEY']
assistant_id = 'asst_mvg3s2IB6NBVDUMVQAyhLAmb'
# thread_id = 'thread_RBShV8Ay9B9n1nmJnAXdbBfy'

header_area = st.empty()
title_area, competitor_area = header_area.columns([4,1])
title_area.title('AI powered Title and Bulletpoints optimizer')
title_area.subheader('Input short product description, current title and bulletpoints along with the most important keywords.')

if competitor_area.checkbox('Add competitor data'):
    competitors = competitor_area.text_area('Competitors', placeholder='Enter ASINs or Amazon.com links (up to 5 perferably)')
    asins_str = re.split(' |,|\n|\t', competitors)
    st.session_state.asins =  [re.search('([A-Z0-9]{10})', x).group().strip() for x in asins_str if re.search('([A-Z0-9]{10})', x)]

product_description_area = st.empty()
title_area1 = st.empty()
title_area2 = st.empty()
bullets_area = st.empty()
keywords_area = st.empty()
button_area = st.empty()
button_col1, button_col2, button_col3 = button_area.columns([3,1,1])
log_area = st.empty()

if 'optimized_title' not in st.session_state:
    st.session_state.optimized_title = ('',True)
if 'optimized_bullets' not in st.session_state:
    st.session_state.optimized_bullets = ('',True)

product = product_description_area.text_area('Describe your product',placeholder='Example: A bed sheet set made of microfiber with 1 flat sheet, 1 fitted sheet and 2 pillowcases')
title_current = title_area1.text_area('Current title', height = 70, max_chars=200, placeholder='Input your current title here')
title_optimized = title_area2.text_area('Optimized title will be shown here', value = st.session_state.optimized_title[0], disabled = st.session_state.optimized_title[1], max_chars=200)

bullets_real_col, bullets_opt_col = bullets_area.columns([1,1])
bullets_real = bullets_real_col.text_area('Current bulletpoints', height = 300, placeholder='Input your current bulletpoints')
bullets_optimized = bullets_opt_col.text_area('Optimized bulletpoints', value = st.session_state.optimized_bullets[0], height = 300, disabled=st.session_state.optimized_bullets[1])

keywords = keywords_area.text_area('Current keywords', placeholder='Input your most important keywords - AI will try to use them in the new title and bulletpoints')

if 'assistant' not in st.session_state:
    client = client = OpenAI(api_key = ASSISTANT_KEY)
    st.session_state['client'] = client
    st.session_state['assistant'] = client.beta.assistants.retrieve(assistant_id)
    # thread = client.beta.threads.retrieve(thread_id = thread_id)

def process(full_prompt):
    client = st.session_state['client']
    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread_id = thread.id,
        role = 'user',
        content = full_prompt)
    
    run = client.beta.threads.runs.create(
        thread_id = thread.id,
        assistant_id = assistant_id)
    time.sleep(0.5)
    if 'status' not in st.session_state:
        st.session_state.status = ['queued']
    while True:
        st.session_state.status = client.beta.threads.runs.retrieve(run_id = run.id, thread_id = thread.id).status
        log_area.write('Please wait')
        time.sleep(0.5)
        log_area.write(st.session_state.status)
        time.sleep(0.5)
        if st.session_state.status =='completed':
            break
    messages = client.beta.threads.messages.list(thread_id = thread.id)
    log_area.write('Done')
    st.session_state.result = messages.data[0].content[0].text.value
    st.session_state.optimized_title = (st.session_state.result.split('|')[0].strip(),False)
    new_bullets = st.session_state.result.split('|')[1:]
    new_bullets = [x.strip() for x in new_bullets]
    new_bullets = '\n\n'.join(new_bullets)
    st.session_state.optimized_bullets =  (new_bullets,False)
    client.beta.threads.delete(thread_id = thread.id)
    st.rerun()

if button_col1.button('Optimize'):# and 'result' not in st.session_state:
    st.session_state.prompt = f'Product:\n{product}\n\nTitle:\n{title_current},\n\nBulletpoints:\n{bullets_real}\n\nKeywords:\n{keywords}'
    if 'asins' in st.session_state and len(st.session_state.asins) > 0:
        items = get_product_details(st.session_state.asins)
        st.session_state.competitors_prompt = '\n\nCompetitors information for reference: ' + ', '.join(['Title: ' + items[x]['title'] + '\nBulletpoints: ' + items[x]['bulletpoints'] for x in items])
        st.session_state.prompt += st.session_state.competitors_prompt
    process(st.session_state.prompt)
if button_col2.button('Try again'):
    if 'result' in st.session_state:
        del st.session_state.result
    process(st.session_state.prompt)
    st.rerun()