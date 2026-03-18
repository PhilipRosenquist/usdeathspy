import pandas as pd

def parse_cdc_data(data_path, meta_path, nrows=None):
    """
    Parses fixed-width CDC data using a metadata map.
    """
    # 1. Load the map we built from the PDF/Excel docs
    meta_df = pd.read_csv(meta_path)
    
    # 2. Prepare the slicing instructions
    # CDC uses 1-based indexing, so we calculate widths
    widths = (meta_df['end'] - meta_df['start'] + 1).tolist()
    names = meta_df['name'].tolist()

    # 3. Define 'String' columns to prevent leading-zero loss
    # We'll target Month and any Recodes that are typically zero-padded
    str_cols = ['month_of_death', 'education', 'sex', 'marital_status']
    # Create a dictionary for the dtype argument
    dtype_settings = {col: str for col in str_cols if col in names}

    # 4. The Heavy Lifting
    # We use 'latin-1' because these old gov files often have 
    # extended ASCII characters that break standard 'utf-8'
    try:
        df = pd.read_fwf(
            data_path, 
            widths=widths, 
            names=names, 
            nrows=nrows, 
            encoding='latin-1',
            dtype=dtype_settings  # Keeps "01" as "01"
        )
        
        print(f"Success! Captured {len(df)} rows.")
        return df

    except Exception as e:
        print(f"Parsing error: {e}")
        return pd.DataFrame() # Return empty if it totally fails