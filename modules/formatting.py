
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

def prepare_for_export(dfs,sheet_names):
    from io import BytesIO
    import pandas as pd
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for df,sheet_name in list(zip(dfs,sheet_names)):
            df.to_excel(writer, sheet_name = sheet_name, index = False)
            format_header(df,writer,sheet_name)
    return output.getvalue()
