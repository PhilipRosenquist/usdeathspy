import os
import requests
import subprocess
import time
from pathlib import Path

def download_cdc_data(data_type, year):
    """
    Downloads and extracts NCHS data.
    """
    base_dir = Path(__file__).resolve().parents[2]
    download_dir = base_dir / "data" / data_type / str(year)
    download_dir.mkdir(parents=True, exist_ok=True)

    # 1. Check for existing data (now checking size, not just existence)
    existing_files = [f for f in download_dir.rglob("*") if f.is_file() and f.stat().st_size > 1024*1024]
    if existing_files:
        print(f"--- Data for {data_type} {year} already exists. Skipping download. ---")
        return download_dir
    year_short = str(year)[-2:]
    
    if data_type == "multiple mortality":
        url = f"https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/mortality/mort{year}us.zip"
        
    elif data_type == "birth cohort":
        # Dynamic year: LinkCO15US.zip -> LinkCO{year_short}US.zip
        url = f"https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/cohortlinkedus/LinkCO{year_short}US.zip"
        
    elif data_type == "births":
        # The data file is usually 'Nat{year_full}us.zip'
        url = f"https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/Nat{year}us.zip"
    
    else:
        raise ValueError(f"Unknown data_type: {data_type}")

    zip_path = download_dir / f"{data_type}_{year}_temp.zip"

    # 2. Stream Download
    print(f"Downloading {data_type} {year} from CDC...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)

    # 3. The Extraction Strategy
    print(f"Extracting {zip_path.name}...")
    
    # Path to 7-Zip (Common default locations)
    seven_zip = r"C:\Program Files\7-Zip\7z.exe"
    
    success = False

    # Attempt 1: 7-Zip (The Best Method)
    if os.path.exists(seven_zip):
        print("Using 7-Zip for high-performance extraction...")
        cmd = [seven_zip, "x", str(zip_path), f"-o{download_dir}", "-y"]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0: success = True

    # Attempt 2: PowerShell Fallback (If 7-Zip is missing)
    if not success and os.name == 'nt':
        print("7-Zip not found. Trying System Fallback (PowerShell)...")
        cmd = ["powershell", "-Command", f"Expand-Archive -Path '{zip_path}' -DestinationPath '{download_dir}' -Force"]
        subprocess.run(cmd, check=True)
        success = True # We check actual file size next to verify

    # 4. THE INTEGRITY CHECK (The "Anti-Ghost" Filter)
    # We wait up to 30 seconds for the OS/Cloud to finalize the file writes
    start_verify = time.time()
    while (time.time() - start_verify) < 30:
        all_files = [f for f in download_dir.rglob("*") if f.is_file() and not f.name.endswith(".zip")]
        if all_files and max(f.stat().st_size for f in all_files) > 0:
            print(f"Extraction verified. Largest file: {max(f.stat().st_size for f in all_files) / 1024**2:.2f} MB")
            success = True
            break
        print("Waiting for filesystem to catch up...", end="\r")
        time.sleep(2)

    if zip_path.exists():
        os.remove(zip_path)

    if not success:
        raise RuntimeError("Extraction failed: Files are empty or missing.")

    return download_dir