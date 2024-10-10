import streamlit as st
from io import BytesIO
from datetime import datetime
import pandas as pd
import re
from modules import formatting as ff
import os

st.subheader('Under construction')
# # import nltk
# # # if not os.path.isdir('/home/appuser/nltk_data'):
# # nltk.download('all')

# # st.set_page_config(page_title = 'Mellanni Keyword processing', page_icon = 'logo.ico',layout="wide")

# # import login
# # st.session_state['login'], st.session_state['username']= login.login()

# import login_google
# st.session_state['login'] = login_google.login()

# if st.session_state['login'][0]:

#     bins = [0.4,0.7]
#     labels = ['low','med','high']
#     n_clusters = 5
#     file, cerebro_file, ba_file, magnet_file,file_ba_matched,file_ba_missed = None, None,None,None,None,None
#     example_asins = ['B08CZVWR21','B07N7KFHVH','B08N2RDBHT','B00HHLNRVE','B07M74PH8P']
#     asin_str = '(B[A-Z0-9]{9})'
#     cerebro_columns = ['Keyword Phrase', 'ABA Total Click Share', 'ABA Total Conv. Share',
#         'Cerebro IQ Score', 'Search Volume','Search Volume Trend','Sponsored ASINs',
#         'Competing Products','CPR','Title Density', 'Amazon Recommended']#,
#         # 'Sponsored', 'Organic',
#         #    'H10 PPC Sugg. Min Bid','H10 PPC Sugg. Max Bid', 'Keyword Sales',
#         #    'Sponsored Rank (avg)', 'Sponsored Rank (count)','H10 PPC Sugg. Bid',
#         #    'Amazon Recommended Rank (avg)', 'Amazon Recommended Rank (count)',
#         #    'Position (Rank)', 'Relative Rank', 'Competitor Rank (avg)',
#         #    'Ranking Competitors (count)', 'Competitor Performance Score']

#     def text_processing(file, cosine = True):
#         from sklearn.feature_extraction.text import TfidfVectorizer
#         from sklearn.cluster import MiniBatchKMeans, KMeans, MeanShift, AgglomerativeClustering, DBSCAN
#         from sklearn.metrics.pairwise import cosine_similarity
#         import nltk
#         if nltk.download('all') == False:
#             nltk.download('all')
#         from nltk.corpus import stopwords
#         from nltk.stem import WordNetLemmatizer
#         import re        
#         cluster_col = 'cluster'
#         corpus_col = 'clean kw'
#         kw_col = [x for x in ['Search Query', 'Keyword Phrase'] if x in file.columns][0]
#         def lemmatize(file, column):
#             kw = file[column].values.tolist()
#             lemmatizer = WordNetLemmatizer()
#             corpus = []
#             for i in range(len(kw)):
#                 r = re.sub('[^a-zA-Z]', ' ', kw[i]).lower().split()
#                 r = [word for word in r if word not in stopwords.words(['english','spanish'])]
#                 r = [lemmatizer.lemmatize(word) for word in r]
#                 r = ' '.join(r)
#                 corpus.append(r)
#             file[corpus_col] = corpus
#             return file
        
#         def measure_clusters(cosine_sim):
#             bins = range(2,30)
#             wcss = []
#             for i in bins:
#                 kmeans = KMeans(n_clusters=i, init='k-means++', max_iter=300, n_init=10, random_state=0)
#                 kmeans.fit(cosine_sim)
#                 wcss.append(kmeans.inertia_)    
#             optimal_clusters = [abs(wcss[i+1]-wcss[i]) for i in range(len(wcss)-1)].index(min([abs(wcss[i+1]-wcss[i]) for i in range(len(wcss)-1)]))
#             return optimal_clusters
        
#         def clusterize_keywords(file, cosine):
#             corpus = file[corpus_col].values.tolist()
#             cv = TfidfVectorizer(stop_words=['english','spanish'],ngram_range=(1,3))
#             vectors = cv.fit_transform(corpus)
#             if cosine:
#                 cosine_sim = cosine_similarity(vectors)
#             else:
#                 cosine_sim = vectors
#             n_clusters = measure_clusters(cosine_sim)
#             st.write(f'Found {n_clusters} clusters')
#             model = KMeans(n_clusters=n_clusters, init='k-means++', max_iter=300, n_init=10, random_state=0)
#             clusters = model.fit_predict(cosine_sim)
#             return clusters
        
#         def name_groups(file):
#             clusters = file[cluster_col].unique().tolist()
#             names = {}
#             for c in clusters:
#                 kws = file[file[cluster_col] == c][kw_col].values.tolist()
#                 kw_list = [w for line in [x.split() for x in kws] for w in line]
#                 counts = pd.DataFrame(kw_list).value_counts()
#                 limit = counts.describe(percentiles = [0.5,0.9])['90%']
#                 counts = counts[counts>limit].index.tolist()
#                 if len(counts) > 5:
#                     names[c] = ' '.join([x[0] for x in counts[:5]]) + ' +'
#                 else:
#                     names[c] = ' '.join([x[0] for x in counts])
#                 file[cluster_col] = file[cluster_col].replace(names)
#             return file
#         file = lemmatize(file, kw_col)
#         clusters = clusterize_keywords(file, cosine = cosine)
#         file[cluster_col] = clusters
#         file = name_groups(file)
#         del file['clean kw']
#         return file


#     def lemmatize(file, column):
#         import nltk
#         # if nltk.download('all') == False:
#             # nltk.download('all')
#         from nltk.corpus import stopwords
#         from nltk.stem import WordNetLemmatizer
#         from sklearn.feature_extraction.text import CountVectorizer
#         import re
#         kw = file[column].values.tolist()
#         lemmatizer = WordNetLemmatizer()
#         corpus = []
#         for i in range(len(kw)):
#             r = re.sub('[^a-zA-Z]', ' ', kw[i]).lower().split()
#             r = [word for word in r if word not in stopwords.words('english')]
#             r = [lemmatizer.lemmatize(word) for word in r]
#             r = ' '.join(r)
#             corpus.append(r)
#         file['clean kw'] = corpus
#         cv = CountVectorizer()
#         vectors = cv.fit_transform(kw)
#         word_freq = {}
#         for text in corpus:
#             words = text.split(' ')
#             for word in words:
#                 if word in word_freq:
#                     word_freq[word] +=1
#                 else:
#                     word_freq[word] = 1
#         word_freq = pd.DataFrame.from_dict(word_freq, orient = 'index').reset_index()
#         word_freq.columns = ['word','frequency']
#         word_freq = word_freq.sort_values('frequency', ascending = False)
#         sums = {}
#         top_words = {}
#         for keyword in corpus:
#             text = keyword.split(' ')
#             score = sum(word_freq[word_freq['word'].isin(text)]['frequency'])
#             sums[keyword] = score
#             top_words[keyword] = ' '.join(word_freq[word_freq['word'].isin(text)].sort_values('frequency', ascending = False)['word'].values[:3])
#         sums = pd.DataFrame.from_dict(sums, orient = 'index', columns = ['frequency score'])
#         top_words = pd.DataFrame.from_dict(top_words, orient = 'index', columns = ['top_word(s)'])
#         file = pd.merge(file, sums, left_on = 'clean kw', right_index = True)
#         file = pd.merge(file, top_words, left_on = 'clean kw', right_index = True)
#         file = file[[column,'frequency score','top_word(s)']]
        
#         return file, word_freq, vectors

#     def clusterize(file,vectors,cols,num_clusters):
#         from sklearn.cluster import KMeans
#         model = KMeans(n_clusters = num_clusters, n_init='auto')
#         if vectors is not None:
#             model.fit(vectors)
#             file['word similarity'] = model.labels_
#         else:
#             model.fit(file[cols])
#             file['cluster'] = model.labels_
#         return file

#     # @st.cache(suppress_st_warning=True)
#     def process_file(asins,cerebro,ba,magnet,n_clusters,bins, file_ba_matched = file_ba_matched, file_ba_missed = file_ba_missed):
#         bin_labels = [str(int(x*100))+'%' for x in bins]

#         file = cerebro.copy()
#         if 'Keyword Sales' not in file.columns:
#             file['Keyword Sales'] = 0

#         if len(asins) == 1:
#             stat_columns = ['Keyword Phrase','ABA Total Click Share','Keyword Sales','Search Volume','CPR']#,'Ranking Competitors (count)']
#         elif len(asins)>1:
#             stat_columns = ['Keyword Phrase','ABA Total Click Share','Keyword Sales','Search Volume','CPR','Ranking Competitors (count)']
#         asin_columns = asins.copy()
#         r = len(stat_columns)
#         all_columns = stat_columns+asin_columns
#         file = file[all_columns]
#         file = file[file['Search Volume'] != '-']
#         file['Search Volume'] = file['Search Volume'].astype(int)
#         file['Keyword Sales'] = file['Keyword Sales'].replace('-',0)
#         file['Keyword Sales'] = file['Keyword Sales'].astype(int)
#         file = file.sort_values('Search Volume', ascending = False)
#         file = file.replace('>306',306).replace('N/R',306).replace('-',306)#.replace(0,306)
#         file.iloc[:,r:] = file.iloc[:,r:].astype(int)
#         file['Top30'] = round(file.iloc[:,r:].isin(range(1,31)).sum(axis = 1)/len(asins),2)
#         file['Top10'] = round(file.iloc[:,r:-1].isin(range(1,11)).sum(axis = 1)/len(asins),2)
#         file['KW conversion'] = round(file['Keyword Sales'] / file['Search Volume'] * 100,2)
#         file['Sales normalized'] = (file['Keyword Sales']-file['Keyword Sales'].min())/(file['Keyword Sales'].max()-file['Keyword Sales'].min())
#         file['Conversion normalized'] = (file['KW conversion']-file['KW conversion'].min())/(file['KW conversion'].max()-file['KW conversion'].min())
#         file['SV normalized'] = (file['Search Volume']-file['Search Volume'].min())/(file['Search Volume'].max()-file['Search Volume'].min())
#         file["Sergey's score"] = round(
#             file['Conversion normalized']*1.1+file['Sales normalized']*.8+file['Top30']*2+file['Top10'],
#             3)
#         file["Sergey's score"] = round(((file["Sergey's score"]-file["Sergey's score"].min())
#                                 / (file["Sergey's score"].max()-file["Sergey's score"].min()))*100,1)
#         file = file.sort_values(["Sergey's score"],ascending = False)
#         search_terms = file['Keyword Phrase'].drop_duplicates().tolist()

#     # define alpha-asins
#         sums = []
#         percs = []
#         if sum(file['Keyword Sales']) == 0:
#             metrics = ['Search Volume','% share by search volume']
#         else:
#             metrics = ['Keyword Sales', '% share by sales']
#         for a in asin_columns:
#             n = file.loc[(file[a].between(1,30))][metrics[0]].sum()
#             sums.append(n)

#         for a in sums:
#             p = a/sum(sums)
#             percs.append(p)

#         sums_db = pd.DataFrame([sums,percs], columns = asin_columns, index = [metrics[0],metrics[1]])
#         sums_db.loc[metrics[1]] = round(sums_db.loc[metrics[1]].astype(float)*100,1)
        
#         # get Brand Analytics file results
#         if isinstance(ba,pd.core.frame.DataFrame):

#             file_ba = ba.copy()
                
#             file_ba = file_ba.drop('Department', axis = 1)
#             file_ba_missed = file_ba[~file_ba['Search Term'].isin(search_terms)]
#             file_ba_matched = file_ba[file_ba['Search Term'].isin(search_terms)]
#             sv = file.copy()
#             sv = sv[['Keyword Phrase','Keyword Sales']]
#             sv['Search Term'] = sv['Keyword Phrase'].copy()
#             sv = sv.drop('Keyword Phrase', axis = 1)
#             file_ba_matched = pd.merge(file_ba_matched,sv,on = 'Search Term', how = 'left')
            
#         #apply boolean conditions to sales,conversion and relevance
#         #alternative way using pandas cut
#         try:
#             file['sales'] = pd.cut(
#                 file['Sales normalized'],
#                 bins = [-1,
#                     file['Sales normalized'].describe(percentiles = bins)[bin_labels[0]],
#                     file['Sales normalized'].describe(percentiles = bins)[bin_labels[1]],
#                     1],
#                 labels = ['low','med','high'],
#                 duplicates = 'drop'
#                 )
#         except:
#             file['sales'] = 'none'
#         try:
#             file['conversion'] = pd.cut(
#                 file['Conversion normalized'],
#                 bins = [-1,
#                     file['Conversion normalized'].describe(percentiles = bins)[bin_labels[0]],
#                     file['Conversion normalized'].describe(percentiles = bins)[bin_labels[1]],
#                     1],
#                 labels = ['low','med','high'],
#                 duplicates= 'drop'
#                 )
#         except:
#             file['conversion'] = 'none'

#         file['competition'] = pd.cut(
#             file['Top30'],bins = 3,labels = labels, duplicates = 'drop'
#             )

#         sales_cols = pd.get_dummies(file['sales'],prefix = 'sales')
#         conversion_cols = pd.get_dummies(file['conversion'],prefix = 'conversion')
#         competition_cols = pd.get_dummies(file['competition'],prefix = 'competition')
#         file = pd.concat([file,sales_cols,conversion_cols,competition_cols], axis = 1)
#         clusterize_columns = sales_cols.columns.tolist()+conversion_cols.columns.tolist()+competition_cols.columns.tolist()
#         normalized_columns = ['Sales normalized','Conversion normalized','SV normalized']
        
        
#         # feed the file to KMeans model to clusterize
#         file = clusterize(file,vectors = None,cols = clusterize_columns,num_clusters = n_clusters)
#         # visualize_clusters(file,columns,n_clusters)
#         file = file.drop(clusterize_columns, axis = 1)
#         file = file.drop(normalized_columns, axis = 1)

        
#         top_kws = file['Keyword Phrase'].head(10).tolist()
#         cerebro_kws = file['Keyword Phrase'].unique()
        
#         # st.session_state['magnet_words'] = magnet_words
#         if isinstance(magnet,pd.core.frame.DataFrame):
#             magnet = magnet[~magnet['Keyword Phrase'].isin(cerebro_kws)]
                
#             magnet = magnet[magnet['Search Volume'] != '-']
#             magnet['Search Volume'] = magnet['Search Volume'].str.replace(',','').astype(int)
#             if 'keyword sales' in [x.lower() for x in magnet.columns]:
#                 magnet['Keyword Sales'] = magnet['Keyword Sales'].replace('-',0).replace(',','')
#                 magnet['Keyword Sales'] = magnet['Keyword Sales'].astype(int)
#                 magnet['KW conversion'] = round(magnet['Keyword Sales'] / magnet['Search Volume'] * 100,2)
#                 magnet = magnet.sort_values('KW conversion', ascending = False)
#             magnet_cols = magnet.columns.tolist()
#             file_cols = file.columns.tolist()
#             drop_cols = list(set(magnet_cols) - set(file_cols))
#             magnet = magnet.drop(drop_cols,axis = 1)
#             file = pd.concat([file,magnet],axis = 0)

#         #add word counts and frequency scores
#         # lemm, word_freq, vectors = lemmatize(file, 'Keyword Phrase')
#         # file = pd.merge(file, lemm, how = 'left', on = 'Keyword Phrase')
#         # file = clusterize(file,vectors,cols = None,num_clusters=8)
#         word_freq = None
#         file = file = text_processing(file, cosine = True)
#         return file, sums_db, file_ba_matched,file_ba_missed, word_freq, asins,top_kws,metrics

#     st.title('Keyword processing tool')
#     asins_area, magnet_col, alpha_asin = st.columns(3)
#     magnet_words = magnet_col.empty()

#     link = '[Goto Cerebro](https://members.helium10.com/cerebro?accountId=268)'
#     st.markdown(link, unsafe_allow_html=True)

#     df_slot = st.empty()

#     def clear_filters():
#         file = st.session_state['file']
#         st.session_state['include'] = ''
#         st.session_state['exclude'] = ''
#         df_slot.write(file)

#     with st.sidebar:
#         st.header('Apply filters (EXPERIMENTAL!)')
#         include_area,exclude_area, kw_area = st.container(), st.container(), st.container()
#         include = include_area.text_input('Words to include?',key = 'include')
#         include_all = include_area.radio('Include mode:',['All','Any'],horizontal = True)
#         exclude = exclude_area.text_input('Words to exclude?', key = 'exclude')
#         exclude_all = exclude_area.radio('Exclude mode:',['All','Any'],horizontal = True)
#         if 'kws' in st.session_state:
#             kw_group = kw_area.selectbox('Keyyword groups',['All']+st.session_state['kws'])
#             if kw_group and kw_group != 'All':
#                 st.session_state['display_file'] = st.session_state['file'][st.session_state['file']['cluster'] == kw_group]
#                 df_slot.write(st.session_state['file']['cluster'] == kw_group)
#             elif kw_group == 'All':
#                 df_slot.write(st.session_state['display_file'])
#         st.button('Clear filters', on_click= clear_filters)

#     with st.expander('Upload files'):
#         cerebro_file = st.file_uploader('Select Cerebro file')
#         if cerebro_file:
#             if '.csv' in cerebro_file.name:
#                 cerebro = pd.read_csv(cerebro_file).fillna(-1)
#             elif '.xlsx' in cerebro_file.name:
#                 cerebro = pd.read_excel(cerebro_file).fillna(-1)
#             if all([x in cerebro.columns for x in cerebro_columns]):
#                 asins = [re.findall(asin_str, x) for x in cerebro.columns]
#                 try:
#                     try:
#                         asin = re.search(asin_str,cerebro_file.name).group()
#                     except:
#                         asin = 'Unidentified'
#                     asins = [asin] + [x[0] for x in asins if x != []]
#                     if len(asins) == 1:
#                         asin_col = 'Organic Rank'
#                     else:
#                         asin_col = 'Position (Rank)'
#                     cerebro = cerebro.rename(columns = {asin_col:asin})
#                 except:
#                     asins = [asin_col] + [x[0] for x in asins if x != []]
#                 asins_area.text_area('ASINs in Cerebro file:','\n'.join(asins), height = 250)
#                 st.write(f'Uploaded successfully, file contains {len(cerebro)} rows')
#             else:
#                 st.warning('This is not a Cerebro file!')
#                 st.stop()

#         if st.checkbox('Add Brand Analytics file (optional), .csv or .xlsx supported'):
#             ba_file = st.file_uploader('Select Brand Analytics file')
#         if ba_file:
#             if '.csv' in ba_file.name:
#                 ba = pd.read_csv(ba_file, skiprows = 1)
#             elif '.xlsx' in ba_file.name:
#                 ba = pd.read_excel(ba_file, skiprows = 1)
#             st.write(f'Uploaded successfully, file contains {len(ba)} rows')
#         else:
#             ba = ''

#         if st.checkbox('Add Magnet file (optional), .csv or .xlsx supported'):
#             magnet_file = st.file_uploader('Select Magnet file')
#         if magnet_file:
#             if '.csv' in magnet_file.name:
#                 magnet = pd.read_csv(magnet_file)
#             elif '.xlsx' in magnet_file.name:
#                 magnet = pd.read_excel(magnet_file)
#             st.write(f'Uploaded successfully, file contains {len(magnet)} rows')
#         else:
#             magnet = ''



#     if 'display_file' in st.session_state:
#         df_slot.write(st.session_state['display_file'])
        

#     if st.button('Process keywords') and cerebro_file:
#         file, sums_db, file_ba_matched,file_ba_missed, word_freq,asins,top_kws,metrics = process_file(asins,cerebro,ba,magnet,n_clusters,bins)
#         st.session_state['file'] = file
#         alpha_asin.bar_chart(sums_db.T[metrics[1]])
#         magnet_words.text_area('Magnet keyword research', value = "\n".join(top_kws), height = 250)
#         st.session_state['display_file'] = file.drop(columns = asins)
#         st.session_state['df'] = st.session_state['display_file']
#         st.session_state['kws'] = file['cluster'].unique().tolist()
#         df_slot.write(st.session_state['display_file'])
        
#         st.session_state['output'] = BytesIO()
#         with pd.ExcelWriter(st.session_state['output'], engine='xlsxwriter') as writer:
#             file.to_excel(writer, sheet_name = 'Keywords', index = False)
#             workbook = writer.book
#             worksheet = writer.sheets['Keywords']
#             ff.format_header(file,writer,'Keywords')
#             max_row, max_col = file.shape
#             worksheet.conditional_format(
#                 1,max_col-1,max_row,max_col-1,
#                 {'type': '3_color_scale','max_color':'red','min_color':'green'})
#             try:
#                 magnet_row = len(file)-len(magnet)
#                 bg = workbook.add_format({'bg_color': 'red'})
#                 worksheet.conditional_format(
#                     magnet_row+1,0,max_row,0,{'type':'no_blanks','format':bg})
#             except:
#                 pass
            
#             sums_db.to_excel(writer, sheet_name = 'Alpha ASIN', index = False)
#             ff.format_header(sums_db, writer, 'Alpha ASIN')
#             worksheet = writer.sheets['Alpha ASIN']
#             worksheet.conditional_format(
#                 2,0,2,max_col-1,
#                 {'type': '3_color_scale','max_color':'red','min_color':'green'})
#             try:
#                 file_ba_matched.to_excel(writer, sheet_name = 'BA_match', index = False)
#                 ff.format_header(file_ba_matched, writer, 'BA_match')
#                 file_ba_missed.to_excel(writer, sheet_name = 'BA_missed', index = False)
#                 ff.format_header(file_ba_missed, writer, 'BA_missed')
#             except:
#                 pass
#             try:
#                 color_kws.to_excel(writer, sheet_name = 'Color KWs', index = False)
#                 worksheet = writer.sheets['Color KWs']
#                 ff.format_header(color_kws,writer,'Color KWs')
#                 max_row, max_col = color_kws.shape
#                 worksheet.conditional_format(
#                     1,max_col-1,max_row,max_col-1,
#                     {'type': '3_color_scale','max_color':'red','min_color':'green'})
#             except:
#                 pass
#             try:
#                 word_freq.to_excel(writer, sheet_name = 'word_frequency', index = False)
#                 ff.format_header(word_freq, writer, 'word_frequency')
#             except:
#                 pass
#     if any(['display_file' in st.session_state, 'df' in st.session_state]):
#         st.download_button('Download results',st.session_state['output'].getvalue(), file_name = 'test.xlsx')

#     def filter_plus(file,filters, combination):
#         words = [w.lower().strip() for w in filters.split(',')]
#         if combination == 'Any':
#             return file[file['Keyword Phrase'].str.contains('|'.join(words),case = False)]
#         elif combination == 'All':
#             return file[file['Keyword Phrase'].str.split(' ').apply(set(words).issubset)]
        
#     def filter_minus(file,filters, combination):
#         words = [w.lower().strip() for w in filters.split(',')]
#         if combination == 'Any':
#             return file[~file['Keyword Phrase'].str.contains('|'.join(words),case = False)]
#         elif combination == 'All':
#             return file[~file['Keyword Phrase'].str.split(' ').apply(set(words).issubset)]


#     if include != '' and 'df' in st.session_state:
#         if 'filtered_df' in st.session_state:
#             st.session_state['filtered_file'] = st.session_state['filtered_df']
#         else:
#             st.session_state['filtered_file'] = st.session_state['df']
#         st.session_state['filtered_file'] = filter_plus(st.session_state['filtered_file'],include, include_all)
#         if len(st.session_state['filtered_file'] == 0):
#             df_slot.write('Nothing matched')
#         else:
#             st.session_state['filtered_df'] = st.session_state['filtered_file']
#             df_slot.write(st.session_state['filtered_file'])

#     if exclude != '' and 'df' in st.session_state:
#         if 'filtered_df' in st.session_state:
#             filtered_file = st.session_state['filtered_df']
#         else:
#             filtered_file = st.session_state['df']
#         filtered_file = filter_minus(filtered_file,exclude, exclude_all)
#         if len(filtered_file == 0):
#             df_slot.write('Nothing matched')
#         else:
#             st.session_state['filtered_df'] = filtered_file
#             df_slot.write(filtered_file)


# # date1,date2 = st.slider(
# #     "Select date range",
# #     min_value = datetime(2020,1,1), max_value = datetime(2023,1,1),
# #     value=(datetime(2021,1,1),datetime(2022,1,1)),
# #     format="MM/DD/YY", 
# #     )
# # st.write("Start time:", date1.strftime("%Y-%m-%d"),' - ', date2.strftime("%Y-%m-%d"))
