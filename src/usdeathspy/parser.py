import polars as pl
from pathlib import Path

def parse_cdc_data(data_path, meta_path, nrows=None):
    # 1. Standard string columns (lowercase)
    STRING_OVERRIDES = {
        'month_of_death', 'education', 'sex', 'marital_status', 
        'race', 'hispanic_origin', 'county_of_residence', 'state_of_residence'
    }

    # 2. Load metadata
    meta = pl.read_csv(meta_path)
    
    # 3. Scan the raw data
    raw_query = pl.scan_csv(
        data_path,
        has_header=False,
        separator="\0",       # Use null byte to treat line as one column
        quote_char=None,      # CRITICAL: Don't let random quotes swallow rows
        new_columns=["raw_line"],
        truncate_ragged_lines=True,
        encoding="utf8-lossy", 
        low_memory=True
    )

    if nrows:
        raw_query = raw_query.head(nrows)

    expressions = []
    
    # Ensure start/end are integers in case the CSV loaded them as strings
    names = meta["name"].to_list()
    starts = meta["start"].cast(pl.Int64).to_list()
    ends = meta["end"].cast(pl.Int64).to_list()

    for name, start, end in zip(names, starts, ends):
        s = start - 1
        l = end - start + 1
        
        # Fixed-width slice
        field = pl.col("raw_line").str.slice(s, l).str.strip_chars()

        if name.lower() in STRING_OVERRIDES:
            expressions.append(field.alias(name))
        else:
            # strict=False handles empty spaces or non-numeric flags gracefully
            expressions.append(field.cast(pl.Int64, strict=False).alias(name))

    try:
        df = raw_query.select(expressions).collect()
        
        if df.height > 0:
            print(f"Success! Captured {df.height} rows using Polars.")
        else:
            print("Warning: Parser returned 0 rows. Check file path or quote settings.")
            
        return df

    except Exception as e:
        print(f"Polars Parsing Error: {e}")
        return pl.DataFrame(schema={n: pl.Utf8 for n in names})