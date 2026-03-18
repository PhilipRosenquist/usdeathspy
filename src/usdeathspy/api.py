import os
import time
from pathlib import Path
from .downloader import download_cdc_data
from .parser import parse_cdc_data

def load_data(data_type, year):
    pkg_root = Path(__file__).resolve().parents[2]
    data_dir = download_cdc_data(data_type, year)
    
    metadata_dir = pkg_root / "src" / "usdeathspy" / "metadata"
    meta_matches = [
        f for f in metadata_dir.glob("*.csv") 
        if data_type.lower() in f.name.lower() and str(year) in f.name
    ]
    
    if not meta_matches:
        raise FileNotFoundError(f"Metadata missing in {metadata_dir}")
    meta_path = meta_matches[0]
    
    all_files = [
        f for f in data_dir.rglob("*") 
        if f.is_file() and "copy" not in f.name.lower()
    ]
    
    if not all_files:
        raise FileNotFoundError(f"No valid data files found in {data_dir}.")

    # Grab the actual heavyweight
    raw_data_path = max(all_files, key=lambda f: f.stat().st_size)

    # Hydration logic (keep this, it's good defensive engineering)
    if raw_data_path.stat().st_size == 0:
        print(f"Hydrating {raw_data_path.name}...")
        try:
            with open(raw_data_path, 'rb') as f:
                f.read(1)
        except:
            pass
        
        start = time.time()
        while raw_data_path.stat().st_size == 0 and (time.time() - start) < 60:
            time.sleep(1)

    print(f"Parsing {raw_data_path.name} ({raw_data_path.stat().st_size / 1024**2:.2f} MB)...")
    return parse_cdc_data(raw_data_path, meta_path)