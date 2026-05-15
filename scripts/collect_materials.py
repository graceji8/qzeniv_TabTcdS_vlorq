import os
import sys
import argparse
import subprocess
import requests
from datetime import datetime
import json

# Try to import required libraries and prompt to install if missing
try:
    import wikipedia
except ImportError:
    print("Warning: 'wikipedia' library not found. Run 'pip install wikipedia'")
    wikipedia = None

try:
    from duckduckgo_search import DDGS
except ImportError:
    print("Warning: 'duckduckgo_search' library not found. Run 'pip install duckduckgo-search'")
    DDGS = None

# Ensure we can import upload_results
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

try:
    from upload_results import get_drive_service, get_drive_folder_id, get_drive_folder_contents, create_drive_folder
except ImportError as e:
    print(f"Error importing upload_results: {e}")
    sys.exit(1)

MATERIALS_FOLDER_ID = "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6"
PROCESSED_PEOPLE = set()

def checkpoint(msg, **kwargs):
    ts = datetime.now().strftime("%H:%M:%S")
    kwargs.setdefault("flush", True)
    print(f"[{ts}] CHECKPOINT: {msg}", **kwargs)

def fetch_processed_people(service):
    """Fetch the list of already processed people from Google Drive."""
    global PROCESSED_PEOPLE
    if not service:
        return
    
    checkpoint(f"Fetching processed people list from Drive (Folder: {MATERIALS_FOLDER_ID})...")
    try:
        materials_id = get_drive_folder_id(service, "materials", MATERIALS_FOLDER_ID)
        if not materials_id:
            materials_id = create_drive_folder(service, "materials", MATERIALS_FOLDER_ID)
            
        folders = get_drive_folder_contents(service, materials_id) if materials_id else {}
        if not folders:
            PROCESSED_PEOPLE = set()
            return
            
        processed = set()
        for name, info in folders.items():
            processed.add(name.replace("_", " ").strip())
        
        PROCESSED_PEOPLE = processed
        checkpoint(f"Found {len(PROCESSED_PEOPLE)} individuals in 'materials' subfolder.")
    except Exception as e:
        checkpoint(f"Could not fetch processed people list: {e}")

def get_wikipedia_summary(person_name, output_path):
    if not wikipedia:
        checkpoint("Skipping Wikipedia fetch (library missing).")
        return False
        
    checkpoint(f"Fetching Wikipedia summary for {person_name}...")
    try:
        summary = wikipedia.summary(person_name, sentences=5, auto_suggest=False)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)
        checkpoint("Wikipedia summary saved.")
        return True
    except wikipedia.exceptions.DisambiguationError as e:
        checkpoint(f"Disambiguation error for {person_name}: {e.options[:5]}")
    except wikipedia.exceptions.PageError:
        checkpoint(f"Page not found for {person_name}.")
    except Exception as e:
        checkpoint(f"Error fetching Wikipedia: {e}")
    return False

def get_location_info(person_name, output_path):
    """Extract birthplace/location from Wikipedia page content."""
    if not wikipedia:
        checkpoint("Skipping location fetch (library missing).")
        return False

    checkpoint(f"Fetching location info for {person_name}...")
    try:
        page = wikipedia.page(person_name, auto_suggest=False)
        content = page.content
        import re

        # Try to find "born in <Location>" or "born ... <City>, <Country>"
        born_patterns = [
            r'born[^.]*?in\s+([A-Z][\w\s,]+(?:,\s*[A-Z][\w\s]+)*)',
            r'born\s+(?:on\s+)?[A-Za-z]+\s+\d{1,2},?\s+\d{4},?\s+in\s+([A-Z][\w\s,]+)',
            r'born\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}[^.]*?in\s+([A-Z][\w\s,]+)',
        ]

        birthplace = None
        for pat in born_patterns:
            m = re.search(pat, content)
            if m:
                birthplace = m.group(1).strip().rstrip('.')
                # Trim to something reasonable
                if len(birthplace) > 80:
                    birthplace = birthplace[:80]
                break

        # Also grab the first sentence which often has location context
        first_sentence = content.split('.')[0] if content else ''

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"Person: {person_name}\n")
            if birthplace:
                f.write(f"Birthplace: {birthplace}\n")
            else:
                f.write(f"Birthplace: (not found automatically)\n")
            f.write(f"\nFirst sentence: {first_sentence}\n")

        checkpoint(f"Location saved: {birthplace or 'not found'}")
        return True
    except Exception as e:
        checkpoint(f"Error fetching location: {e}")
    return False

def search_and_download_images(person_name, folder_path):
    checkpoint(f"Searching for images of {person_name}...")
    try:
        from bing_image_downloader import downloader
        import shutil
        import tempfile
        
        queries = {
            "child": f"{person_name} child photo",
            "young": f"{person_name} young photo",
            "older": f"{person_name} recent older photo"
        }
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            for stage, query in queries.items():
                try:
                    downloader.download(query, limit=1, output_dir=tmpdirname, adult_filter_off=False, force_replace=True, timeout=10, verbose=False)
                    query_dir = os.path.join(tmpdirname, query)
                    if os.path.exists(query_dir):
                        files = os.listdir(query_dir)
                        if files:
                            src_img = os.path.join(query_dir, files[0])
                            dest_img = os.path.join(folder_path, f"photo_{stage}.jpg")
                            shutil.move(src_img, dest_img)
                            checkpoint(f"Downloaded {stage} photo.")
                except Exception as e:
                    checkpoint(f"Failed to download {stage} photo: {e}")
                    
    except ImportError:
        checkpoint("bing-image-downloader not installed. Run 'pip install bing-image-downloader'")
    except Exception as e:
        checkpoint(f"Error fetching images: {e}")

def search_reference_videos(person_name, output_path):
    checkpoint(f"Searching for reference videos for {person_name}...")
    query = f"{person_name} interview speech"
    
    try:
        if DDGS:
            results = list(DDGS().videos(keywords=query, max_results=3))
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"Reference videos for {person_name}:\n\n")
                for r in results:
                    title = r.get('title', 'Unknown Title')
                    url = r.get('content', '')
                    f.write(f"Title: {title}\nURL: {url}\n\n")
            checkpoint("Reference videos saved.")
        else:
            checkpoint("duckduckgo_search not installed, skipping video search.")
    except Exception as e:
        checkpoint(f"Error fetching video links: {e}")

def main():
    parser = argparse.ArgumentParser(description="Collect supplemental materials for famous people.")
    parser.add_argument("--person", type=str, help="Specific person to process (e.g., 'Elon Musk')")
    parser.add_argument("--all", action="store_true", help="Process all people found in the Google Drive materials folder")
    args = parser.parse_args()

    service = get_drive_service()
    if not service:
        checkpoint("Error: Could not connect to Google Drive. Check credentials.")
        return

    temp_base = os.path.join(script_dir, "temp_workspace")
    os.makedirs(temp_base, exist_ok=True)
    
    upload_script = os.path.join(script_dir, "upload_results.py")

    people_to_process = []
    
    if args.person:
        people_to_process.append(args.person)
    elif args.all:
        checkpoint("Looping through current subfolders in temp_workspace...")
        if os.path.exists(temp_base):
            for item in os.listdir(temp_base):
                if os.path.isdir(os.path.join(temp_base, item)):
                    person_name = item.replace("_", " ")
                    people_to_process.append(person_name)
        if not people_to_process:
            checkpoint("No subfolders found in temp_workspace.")
    else:
        checkpoint("Please specify either --person 'Name' or --all.")
        parser.print_help()
        return

    for person in people_to_process:
        checkpoint(f"\n--- Processing materials for {person} ---")
        folder_name = person.replace(" ", "_")
        folder_path = os.path.join(temp_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        wiki_path = os.path.join(folder_path, "wikipedia.txt")
        vid_path = os.path.join(folder_path, "reference_videos.txt")
        loc_path = os.path.join(folder_path, "location.txt")
        
        get_wikipedia_summary(person, wiki_path)
        get_location_info(person, loc_path)
        search_and_download_images(person, folder_path)
        search_reference_videos(person, vid_path)
        
        checkpoint(f"Uploading materials for {person} to Google Drive...")
        try:
            subprocess.run([
                sys.executable, upload_script,
                folder_path, 
                "--name", folder_name, 
                "--parent", MATERIALS_FOLDER_ID, 
                "--parent-name", "materials",
                "--exclude", "full.wav", "ref.wav", "cloned.wav"
            ], check=True)
            checkpoint(f"Successfully uploaded materials for {person}.")
        except subprocess.CalledProcessError as e:
            checkpoint(f"Upload failed for {person}: {e}")

if __name__ == "__main__":
    main()
