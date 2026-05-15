import os
import sys
import logging
import traceback

# Add the scripts directory to path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

import upload_results

# Try socks5:// instead of socks5h://
os.environ["YTDLP_PROXY"] = "socks5://127.0.0.1:1080"
os.environ["http_proxy"] = "socks5://127.0.0.1:1080"
os.environ["https_proxy"] = "socks5://127.0.0.1:1080"

# Hardcoded Folder ID from process_famous_people.py
MATERIALS_FOLDER_ID = "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6"

def test_fetch():
    print(f"Testing fetch from Folder ID: {MATERIALS_FOLDER_ID}")
    
    # Check if proxy is reachable
    import requests
    try:
        print(f"Checking if proxy is reachable (using {os.environ['http_proxy']})...")
        r = requests.get("https://www.google.com", timeout=10)
        print(f"Proxy check: {r.status_code}")
    except Exception as e:
        print(f"Proxy check FAILED: {e}")
    
    service = upload_results.get_drive_service()
    if not service:
        print("FAILED: Could not get Google Drive service.")
        return

    print("Successfully obtained Drive service.")
    
    try:
        # Test getting folder info first
        print("Fetching folder info...")
        folder_info = service.files().get(fileId=MATERIALS_FOLDER_ID, supportsAllDrives=True).execute()
        print(f"Folder Name: {folder_info.get('name')}")
    except Exception as e:
        print(f"FAILED to get folder info: {e}")
        traceback.print_exc()
        return

    print("Attempting to list contents using upload_results.get_drive_folder_contents...")
    try:
        contents = upload_results.get_drive_folder_contents(service, MATERIALS_FOLDER_ID)
        print(f"Fetched {len(contents)} items.")
        for name in sorted(contents.keys()):
            print(f" - {name}")
    except Exception as e:
        print(f"FAILED to fetch contents: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_fetch()
