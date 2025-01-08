import streamlit as st
from typing import Any
from modules import formatting as ff
import textwrap
# from PIL import Image
# from PIL import ImageDraw
from modules import gcloud_modules as gc
from PIL import ImageFont
font = ImageFont.load_default()
from fpdf import FPDF
import pandas as pd
from io import BytesIO
import numpy as np
import os
from barcode import Code128, Code39
from barcode.writer import ImageWriter

import login_google
st.session_state['login'] = login_google.login()
# st.session_state['login'] = (True,'sergey@mellanni.com')

if st.session_state['login'][0]:
    width = 2.2
    height = 0.4
    options_fnsku = {'module_width':height, 'module_height':width+7, 'font_size':10, 'text_distance':4}
    options_itf = {'module_width':height, 'module_height':width+7, 'font_size':12, 'text_distance':4, 'font':font}
    itf_columns = ['SKU','Quantity','UPC','FNSKU']
    template = pd.DataFrame(data = [['sample SKU','required quantity of labels','upc (NOT ITF)','FNSKU (barcode)']], columns = itf_columns)            

    top_area = st.empty()
    bottom_area = st.empty()
    st.divider()
    inv_report_area = st.container()
    col1, col2, col3 = top_area.columns([4,3,2])


    if not os.path.isdir('barcodes'):
        os.makedirs('barcodes')

    def check_skus(sku_list,dictionary):
        test_skus = pd.DataFrame(sku_list, columns=['sku'])
        dict_skus = dictionary['sku'].unique().tolist()
        wrong_skus = test_skus[~test_skus['sku'].isin(dict_skus)]
        if len(wrong_skus) > 0:
            skus_out = '\n'.join(wrong_skus['sku'].unique())
            st.text(f'The following SKUs were not found:\n{skus_out}')
            return False
        return True
        
    def generate_pdf(fnsku_dict, mode='combined'):#fnskus, titles, qty):
        #PDF
        pdf_w = 8.5
        pdf_h = 11
        xmargin = 0.05
        ymargin = 0.5
        x_coords = [round(x,3) for x in np.arange(xmargin,pdf_w-xmargin,((pdf_w-xmargin)-xmargin)/3)+0.15]
        y_coords = [round(y,3) for y in np.arange(ymargin,pdf_h-ymargin,((pdf_h-ymargin)-ymargin)/10)+0.2]
        pdf = FPDF('P', 'in', 'Letter')
        if mode == 'combined':
            pdf.add_page()
            ix = 0
            iy = 0
        for record in fnsku_dict:
            if mode == 'separate':
                ix = 0
                iy = 0
                pdf.add_page()
                pdf.set_font('Arial', style ='', size = 24)
                pdf.text(1,pdf_h/2-0.8,record['sku'])
                pdf.text(1,pdf_h/2-0.4,record['upc'])
                pdf.text(1,pdf_h/2+0.0,record['fnsku'])
                pdf.text(1,pdf_h/2+0.4,record['short_title'])
                pdf.text(1,pdf_h/2+0.8,f"# of labels: {record['qty']}")

            with open(f'barcodes/{record['fnsku']}.png', 'wb') as f:
                Code128(str(record['fnsku']), writer = ImageWriter()).write(f, options = options_fnsku)
            title_str = textwrap.wrap(record['short_title'], width = 40)
            number_barcodes = record['qty']
            
            if mode == 'separate':
                pdf.add_page()
            pdf.set_font('Arial', style ='', size = 8)

            for num_record in range(number_barcodes):
                for p,s in enumerate(title_str):
                    pdf.text(x_coords[ix]+.1+(p/3), y_coords[iy]+0.5+(p/10), s)
                pdf.text(x_coords[ix]+.1, y_coords[iy]+0.6, 'New')
                pdf.image(f'barcodes/{record['fnsku']}.png', x = x_coords[ix], y = y_coords[iy], w = width, h = height, type = '', link = '')
                
                if ix <2:
                    ix += 1
                else:
                    ix = 0
                    iy +=1
                if iy == 10:
                    iy = 0
                    if num_record < number_barcodes-1 or mode=='combined':
                        pdf.add_page()
        # pdf.output('barcodes.pdf', 'F')
        return pdf

    def generate_itf(sku_list,dictionary, layout, qty,leading = '00'):
        if check_skus(sku_list,dictionary):
            pass
        else:
            return None
        if layout == 'Letter':
            pdf_w = 8.5
            pdf_h = 11
            xmargin = 0.05
            ymargin = 0.5
            x_coords = [round(x,3) for x in np.arange(xmargin,pdf_w-xmargin,((pdf_w-xmargin)-xmargin)/3)+0.15]
            y_coords = [round(y,3) for y in np.arange(ymargin,pdf_h-ymargin,((pdf_h-ymargin)-ymargin)/10)+0.2]
            pdf = FPDF('P', 'in', 'Letter')
            #add a title page
            pdf.add_page()
            pdf.set_font('Arial', style ='', size = 42)
            pdf.text(2,pdf_h/2,'ITF14 CODE LIST')
            
        elif layout == 'Zebra':
            pdf_w = 4
            pdf_h = 1.25
            xmargin = 0.05
            ymargin = 0.2
            pdf = FPDF('L', 'in', (1.25,4))
        
        #start barcode pages
        pdf.add_page()
        pdf.set_font('Arial', style ='', size = 11)

        ix = 0
        iy = 0
        for i, sku in enumerate(sku_list):
            file_sku = dictionary[dictionary['sku'] == sku]
            sku_str = textwrap.wrap(sku, width = 25)
            upc = f"{leading}{file_sku['upc'].values[0]}"
            with open(f'barcodes/{sku.replace("-","_")}.png', 'wb') as f:
                Code39(str(upc), writer = ImageWriter(),add_checksum = False).write(f, options = options_itf)
            if layout == 'Letter':
                for p,s in enumerate(sku_str):
                    pdf.text(x_coords[ix]+.1, y_coords[iy]+(p/7), s)
                pdf.image(f'barcodes/{sku.replace("-","_")}.png', x = x_coords[ix], y = y_coords[iy]+0.2, w = width, h = height, type = '', link = '')
                if ix <2:
                    ix += 1
                else:
                    ix = 0
                    iy +=1
                if iy <10:
                    pass
                else:
                    iy = 0
                    pdf.add_page()
            # pdf.add_page()
                    ix = 0
                    iy = 0
            elif layout == 'Zebra':
                for p,s in enumerate(sku_str):
                    pdf.text(xmargin+0.5, ymargin+(p/7), s)
                pdf.image(f'barcodes/{sku.replace("-","_")}.png', x = xmargin+0.3, y = ymargin+0.2, w = width, h = height, type = '', link = '')
                # ymargin += 0.2
                pdf.add_page()
        return pdf

    def remove_images():
        #remove all created png's
        if os.path.isdir('barcodes'):
            files = os.listdir('barcodes')
            for file in files:
                os.remove(os.path.join('barcodes',file))
            os.removedirs('barcodes')
        return None

    with col3:
        # @st.cache_data(show_spinner=False)
        def download_dictionary(full = False):
            st.session_state.market = st.radio('Select marketplace',['US','CA','EU','UK'], horizontal=True)
            dictionary = gc.pull_dictionary(combine = False, market = st.session_state.market, full = full)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                dictionary.to_excel(writer, sheet_name = 'Dictionary', index = False)
                ff.format_header(dictionary,writer,'Dictionary')
            return output.getvalue()
        
        if col3.checkbox('Dictionary'):
            st.session_state.all_cols = False
            if col3.checkbox('Include all columns?'):
                st.session_state.all_cols = True

            dictionary = download_dictionary(full = st.session_state.all_cols)
            col3.download_button('Download dictionary',dictionary, file_name = f'Dictionary_{st.session_state.market}.xlsx')
        if col3.button('Clear'):
            remove_images()
    with col2:
        barcode_type = col2.radio('Select barcode type:',['FNSKU','ITF14','SKU upload with qty'])
        
        if barcode_type == 'ITF14':
            layout = col2.radio('Layout type',['Letter','Zebra'])
            qty_type = 1
            leading = col2.text_input('Leading digits', '00',max_chars=2, placeholder='00')
        elif barcode_type == 'FNSKU':
            layout = 'Letter'
            qty_type = col2.radio('Labels per sheet',[1,30])
        elif barcode_type == 'SKU upload with qty':
            layout = 'Letter'

    with col1:
        if barcode_type in ('ITF14','FNSKU'):
            skus = st.text_area('Input SKUs', height = 300, help = 'Input a list of SKUs you want to generate barcodes for').split('\n')
            sku_list = [x for x in skus if x != '']
        elif barcode_type == 'SKU upload with qty':
            qty_file_obj = st.file_uploader('Upload file with SKUs and quantities (make sure it has columns "sku" and "qty")')
            if qty_file_obj:
                qty_file = pd.read_excel(qty_file_obj)
                sku_list = qty_file['sku'].unique().tolist()
        if col1.button('Create barcodes', icon=':material/barcode:') and len(sku_list) > 0:
            with st.spinner('Please wait'):
                dictionary = gc.pull_dictionary(combine = True)
                check_skus(sku_list,dictionary)
                st.session_state.file = dictionary[dictionary['sku'].isin(sku_list)].reset_index()
                del st.session_state.file['index']

                if barcode_type != 'SKU upload with qty':
                    st.session_state.file['qty'] = qty_type
                else:
                    st.session_state.file = pd.merge(st.session_state.file, qty_file, how = 'outer', on = 'sku')
                
                fnsku_dict = st.session_state.file.to_dict(orient='records')
                
                
                # fnskus = st.session_state.file['fnsku']
                # titles = st.session_state.file['short_title']
                # upcs = st.session_state.file['upc']
                # skus = st.session_state.file['sku']
                # qty = [qty_type]*len(sku_list)
                if barcode_type in ('FNSKU','SKU upload with qty'):
                    st.session_state.pdf = generate_pdf(fnsku_dict, mode='separate' if barcode_type == 'SKU upload with qty' else 'combined')
                    st.session_state.file_name = 'Individual barcodes.pdf'
                elif barcode_type == 'ITF14':
                    qty = qty_type
                    st.session_state.pdf = generate_itf(sku_list,dictionary, layout, qty, leading = leading)
                    st.session_state.file_name = 'ITF14 barcodes.pdf'
                    
        if 'pdf' in st.session_state and st.session_state['pdf'] is not None:
            st.session_state.pdf.output('barcodes/barcodes.pdf', 'F')
            with open('barcodes/barcodes.pdf', "rb") as pdf_file:
                PDFbyte = pdf_file.read()
            remove_images()
            col2.download_button(
                label = 'Download PDF',
                data=PDFbyte,
                file_name = st.session_state.file_name)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                st.session_state.file.to_excel(writer, sheet_name = 'SKUs', index = False)
                ff.format_header(st.session_state.file, writer, 'SKUs')
            col2.download_button(
                label = 'Download SKU list',
                data = output.getvalue(),
                file_name = 'SKU list.xlsx')


    bottom_area.markdown('\nAdditional tool to optimize package dimensions\n\nhttps://package-optimizer.streamlit.app/')

    ###### inventory report section
    if st.session_state['login'][1] in (
        'sergey@mellanni.com','natalie@mellanni.com', 'ruslan@mellanni.com', 'andreia@mellanni.com','dariyka@mellanni.com',
        'karl@mellanni.com','ahmad@mellanni.com'
        ):
        # @st.cache_data
        def download_inv_report(inv_date, market):
            query = f'''SELECT * FROM `reports.fba_inventory_planning` WHERE DATE(snapshot_date)=DATE("{inv_date}") AND marketplace="{market}"'''
            if 'WM' in market:
                if market=='WM':
                    query = f'''SELECT sku, shipNode, 
                                inputQty.amount as input_amount, inputQty.unit as input_unit, 
                                availToSellQty.amount as avail_amount, availToSellQty.unit as avail_unit, 
                                reservedQty.amount as reserved_amount, reservedQty.unit as reserved_unit, 
                                date, item_id 
                                FROM `walmart.inventory` WHERE DATE(date)=DATE("{inv_date}")'''
                elif market=='WM wfs':
                    query = f'SELECT * FROM `walmart.inventory_wfs` WHERE DATE(date)=DATE("{inv_date}")'
            result = client.query(query).to_dataframe()
            inv_report_area.dataframe(result)
        @st.cache_data
        def get_markets():
            markets_query = client.query('SELECT DISTINCT marketplace FROM `reports.fba_inventory_planning`').result()
            return [x[0] for x in markets_query] + ['WM','WM wfs']
        # @st.cache_data
        def get_max_date(market):
            query=f'SELECT MIN(snapshot_date) as min_date, MAX(snapshot_date) as max_date FROM `reports.fba_inventory_planning` WHERE marketplace="{market}"'
            if 'WM' in market:
                if market=='WM':
                    query = 'SELECT MIN(date) as min_date, MAX(date) as max_date FROM `walmart.inventory`'
                elif market=='WM wfs':
                    query = 'SELECT MIN(date) as min_date, MAX(date) as max_date FROM `walmart.inventory_wfs`'
                else:
                    return 0, 0
            
            date_query = client.query(query).result()
            dates = [x for x in date_query]
            return dates[0][0].date(), dates[0][1].date()

        client = gc.gcloud_connect()
        markets = get_markets()
        market_radio = inv_report_area.radio('Select marketplace', markets, index=markets.index('US'), horizontal=True)
        min_date, max_date = get_max_date(market_radio)
        inv_date = inv_report_area.date_input(
            f'Select report date (latest date for {market_radio} is {max_date}, earliest date is {min_date})',
            value=max_date,
            min_value=min_date,
            max_value=max_date
            )
        inv_report_area.button('Download inventory',key='inv_button',icon=':material/inventory_2:', on_click=lambda:download_inv_report(inv_date,market_radio))
    else:
        inv_report_area.write(f'{st.session_state['login'][1]} is not allowed to access this section.\nIf you believe you need access to inventory reports, please contact Sergey')
    