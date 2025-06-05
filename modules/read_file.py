import pandas as pd
import json

def read_file(file_path):
    """
    Reads a file and returns its content as a pandas DataFrame.
    
    Args:
        file_path (str): Path to the file to be read.
        
    Returns:
        pd.DataFrame: DataFrame containing the file content.
    """
    try:
        df = pd.read_csv(file_path)
        # columns = df.columns.tolist()
        # values = df.values.tolist()
        # return columns, values
        df_str = df.to_json(orient='records')
        df_str = df_str.replace('\\/', '/')  # Fix escaped slashes
        print(f"Data from {file_path}:\n{df_str}")
        return df_str
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error