from numpy import inf

def format_header(df,writer,sheet):
    workbook  = writer.book
    cell_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'center', 'font_size':9})
    worksheet = writer.sheets[sheet]
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, cell_format)
    max_row, max_col = df.shape
    worksheet.autofilter(0, 0, max_row, max_col - 1)
    worksheet.freeze_panes(1,0)
    return None

def format_columns(df,writer,sheet,col_num):
    worksheet = writer.sheets[sheet]
    if not isinstance(col_num,list):
        col_num = [col_num]
    else:
        pass
    for c in col_num:
        width = max(df.iloc[:,c].astype(str).map(len).max(),len(df.iloc[:,c].name))
        worksheet.set_column(c,c,width)
    return None

def prepare_for_export(dfs,sheet_names, **kwargs):
    from io import BytesIO
    import pandas as pd
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for df,sheet_name in list(zip(dfs,sheet_names)):
            df.to_excel(writer, sheet_name = sheet_name, index = False)
            if 'numeric_cols' in kwargs.keys():
                num_cols = kwargs['numeric_cols']
                workbook = writer.book
                num_fmt = workbook.add_format({'num_format': '#,##0'})

                worksheet = writer.sheets[sheet_name]
                num_columns = [x for x in df.columns if x in num_cols]
                for num_column in num_columns:
                    col_index = df.columns.tolist().index(num_column)
                    for row, value in enumerate(df[num_column]):
                        if not any([isinstance(value, pd._libs.missing.NAType), value == inf, pd.isna(value)]):
                            worksheet.write(row+1, col_index, value, num_fmt)

            if 'currency_cols' in kwargs.keys():
                curr_cols = kwargs['currency_cols']
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                money_fmt = workbook.add_format({'num_format': '$#,##0.00'})

                curr_columns = [x for x in df.columns if x in curr_cols]
                for curr_column in curr_columns:
                    col_index = df.columns.tolist().index(curr_column)
                    for row, value in enumerate(df[curr_column]):
                        if not any([isinstance(value, pd._libs.missing.NAType), value == inf, pd.isna(value)]):
                            worksheet.write(row+1, col_index, value, money_fmt)

            if 'percent_cols' in kwargs.keys():
                perc_cols = kwargs['percent_cols']
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                percent_fmt = workbook.add_format({'num_format': '0.0%'})

                perc_columns = [x for x in df.columns if x in perc_cols]
                for perc_column in perc_columns:
                    col_index = df.columns.tolist().index(perc_column)
                    for row, value in enumerate(df[perc_column]):
                        if not any([isinstance(value, pd._libs.missing.NAType), value == inf, pd.isna(value)]):
                            worksheet.write(row+1, col_index, value, percent_fmt)
                
            format_header(df,writer,sheet_name)
    return output.getvalue()
