import os
import sys
import argparse
import pickle
import mimetypes
import hashlib
import time
import threading
import fnmatch
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Force UTF-8 for console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Required scopes for Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']

# Thread-local storage for Drive service
thread_local = threading.local()

def get_credentials():
    creds = None
    
    # 1. Try token.pickle (OAuth2 User Token)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    token_path = 'token.pickle'
    if not os.path.exists(token_path):
        token_path = os.path.join(project_root, 'token.pickle')

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            try:
                creds = pickle.load(token)
            except Exception:
                creds = None
    
    # 2. Refresh OAuth2 token if expired
    if creds and creds.valid:
        pass
    elif creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    else:
        creds = None

    # 3. Handle credentials.json
    if not creds:
        creds_path = 'credentials.json'
        if not os.path.exists(creds_path):
            creds_path = os.path.join(project_root, 'credentials.json')

        if not os.path.exists(creds_path):
            print(f"Error: No credentials.json found (checked CWD and {project_root}).")
            return None
        
        # Check if it's a Service Account or OAuth2 Client Secret
        try:
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            
            if creds_data.get('type') == 'service_account':
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(
                    'credentials.json', scopes=SCOPES)
                print("Using Service Account credentials.")
            else:
                # OAuth2 flow (requires token.pickle for non-interactive)
                print("Using OAuth2 Client Secrets (requires token.pickle for non-interactive use).")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                # In GitHub Actions, we can't run_local_server unless it's the first time
                # and the user is running it locally. 
                # But we'll keep the original logic as fallback.
                if 'GITHUB_ACTIONS' not in os.environ:
                    creds = flow.run_local_server(port=0)
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(creds, token)
                else:
                    print("Error: OAuth2 interactive flow cannot run in GitHub Actions without token.pickle")
                    return None
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None

    return creds

def get_drive_service():
    if not hasattr(thread_local, "service"):
        creds = get_credentials()
        if not creds: return None
        thread_local.service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return thread_local.service

def get_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_drive_folder_id(service, folder_name, parent_id=None):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    try:
        results = service.files().list(
            q=query, 
            fields="files(id)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        print(f"DEBUG: Error searching for folder '{folder_name}': {e}")
        return None

def get_drive_folder_contents(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    files_dict = {}
    try:
        # First, verify we can even see the parent folder
        service.files().get(fileId=folder_id, supportsAllDrives=True).execute()
    except Exception as e:
        print(f"DEBUG: Permission error or folder not found for ID '{folder_id}': {e}")
        return {}

    try:
        page_token = None
        while True:
            results = service.files().list(
                q=query, 
                fields="nextPageToken, files(id, name, mimeType, md5Checksum, size)",
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            for f in results.get('files', []):
                files_dict[f['name']] = f
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        return files_dict
    except Exception as e:
        print(f"DEBUG: Error listing contents of folder '{folder_id}': {e}")
        return {}

def apply_drive_folder_tags(service, folder_id, tags):
    if not tags:
        return

    tag_text = ", ".join(tags)
    try:
        service.files().update(
            fileId=folder_id,
            body={
                'description': f"Tags: {tag_text}",
                'appProperties': {
                    'tag': tags[0],
                    'tags': tag_text,
                },
            },
            fields='id',
            supportsAllDrives=True
        ).execute()
    except Exception as e:
        print(f"DEBUG: Error tagging folder '{folder_id}' with '{tag_text}': {e}")

def create_drive_folder(service, folder_name, parent_id=None, tags=None):
    existing_id = get_drive_folder_id(service, folder_name, parent_id)
    if existing_id:
        apply_drive_folder_tags(service, existing_id, tags)
        return existing_id

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if tags:
        tag_text = ", ".join(tags)
        file_metadata['description'] = f"Tags: {tag_text}"
        file_metadata['appProperties'] = {
            'tag': tags[0],
            'tags': tag_text,
        }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    try:
        file = service.files().create(
            body=file_metadata, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        new_id = file.get('id')
        print(f"DEBUG: Created folder '{folder_name}' with ID: {new_id} (Parent: {parent_id})")
        return new_id
    except Exception as e:
        print(f"DEBUG: Error creating folder '{folder_name}': {e}")
        return None

def upload_worker(task):
    local_path, parent_id, existing_file = task
    service = get_drive_service()
    if not service: return
    
    file_name = os.path.basename(local_path)
    
    mimetype, _ = mimetypes.guess_type(local_path)
    if not mimetype: mimetype = 'application/octet-stream'
    media = MediaFileUpload(local_path, mimetype=mimetype, resumable=True)

    if existing_file:
        local_md5 = get_md5(local_path)
        if existing_file.get('md5Checksum') == local_md5:
            return f"SKIPPED: {file_name}"
        else:
            try:
                service.files().update(
                    fileId=existing_file['id'], 
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                return f"UPDATED: {file_name}"
            except Exception as e:
                return f"ERROR updating {file_name}: {e}"

    file_metadata = {'name': file_name}
    if parent_id:
        file_metadata['parents'] = [parent_id]
        
    try:
        service.files().create(
            body=file_metadata, 
            media_body=media,
            supportsAllDrives=True
        ).execute()
        return f"UPLOADED: {file_name}"
    except Exception as e:
        return f"ERROR uploading {file_name}: {e}"

def scan_and_collect(service, local_folder, parent_id=None, drive_folder_name=None, sync=True, exclude=None, include=None, pattern='*', root_path=None, tags=None):
    if not exclude: exclude = []
    if not include: include = []
    if not root_path: root_path = local_folder
    
    if not drive_folder_name:
        drive_folder_name = os.path.basename(local_folder.rstrip(os.sep))
    
    if include:
        rel_folder = os.path.relpath(local_folder, root_path).replace('\\', '/')
        if rel_folder != '.':
            is_match = False
            is_parent = False
            for inc in include:
                inc_p = inc.replace('\\', '/')
                if fnmatch.fnmatch(rel_folder, inc_p) or fnmatch.fnmatch(rel_folder, inc_p + '/*'):
                    is_match = True
                    break
                inc_parts = inc_p.split('/')
                rel_parts = rel_folder.split('/')
                if len(rel_parts) < len(inc_parts):
                    match_so_far = True
                    for i in range(len(rel_parts)):
                        if not fnmatch.fnmatch(rel_parts[i], inc_parts[i]):
                            match_so_far = False
                            break
                    if match_so_far:
                        is_parent = True
                        break
            
            if not is_match and not is_parent:
                return []

    drive_folder_id = create_drive_folder(service, drive_folder_name, parent_id, tags=tags)
    if not drive_folder_id:
        print(f"ERROR: Could not get/create Drive folder '{drive_folder_name}'. Cannot proceed with upload.")
        return []

    tasks = []
    drive_contents = get_drive_folder_contents(service, drive_folder_id) if sync else {}

    for item in os.listdir(local_folder):
        item_path = os.path.join(local_folder, item)
        rel_item = os.path.relpath(item_path, root_path).replace('\\', '/')
        
        if item in ['.git', 'node_modules', '__pycache__', '.env', '.agent'] or item in exclude:
            continue
            
        if include:
            is_match = False
            is_parent = False
            for inc in include:
                inc_p = inc.replace('\\', '/')
                if fnmatch.fnmatch(rel_item, inc_p) or fnmatch.fnmatch(rel_item, inc_p + '/*'):
                    is_match = True
                    break
                
                inc_parts = inc_p.split('/')
                rel_parts = rel_item.split('/')
                if len(rel_parts) < len(inc_parts):
                    match_so_far = True
                    for i in range(len(rel_parts)):
                        if not fnmatch.fnmatch(rel_parts[i], inc_parts[i]):
                            match_so_far = False
                            break
                    if match_so_far:
                        is_parent = True
                        break
            
            if not is_match and not is_parent:
                continue

        if os.path.isdir(item_path):
            tasks.extend(scan_and_collect(service, item_path, drive_folder_id, sync=sync, exclude=exclude, include=include, pattern=pattern, root_path=root_path, tags=tags))
        else:
            if not fnmatch.fnmatch(item, pattern):
                continue
            existing_file = drive_contents.get(item) if sync else None
            tasks.append((item_path, drive_folder_id, existing_file))
            
    return tasks

def main():
    parser = argparse.ArgumentParser(description='Parallel upload to Drive.')
    parser.add_argument('folder', type=str, help='Local folder path.')
    parser.add_argument('--name', type=str, help='Destination folder name on Drive.')
    parser.add_argument('--parent', type=str, help='Parent folder ID on Drive.')
    parser.add_argument('--parent-name', type=str, help='Parent folder name on Drive.')
    parser.add_argument('--exclude', nargs='+', default=[], help='Items to exclude.')
    parser.add_argument('--include', nargs='+', default=[], help='Items to include.')
    parser.add_argument('--pattern', type=str, default='*', help='Glob pattern for files.')
    parser.add_argument('--threads', type=int, default=20, help='Parallel threads.')
    parser.add_argument('--no-sync', action='store_false', dest='sync', help='Disable sync.')
    parser.add_argument('--tag', action='append', default=[], help='Tag metadata to add to created Drive folders.')
    args = parser.parse_args()

    local_path = os.path.abspath(args.folder)
    if not os.path.isdir(local_path):
        print(f"ERROR: Local path is not a directory: {local_path}")
        return

    service = get_drive_service()
    
    parent_id = args.parent
    if args.parent_name:
        parent_id = create_drive_folder(service, args.parent_name, parent_id)
        if not parent_id: return
            
    all_tasks = scan_and_collect(service, local_path, parent_id, args.name, args.sync, args.exclude, args.include, args.pattern, local_path, tags=args.tag)
    
    total = len(all_tasks)
    if total == 0:
        print(f"DEBUG: No files found to upload in {local_path} (after filters/excludes).")
        return

    print(f"DEBUG: Starting parallel upload of {total} files...")
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(upload_worker, task): task for task in all_tasks}
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result:
                print(f"[{i+1}/{total}] {result[:80]}")

if __name__ == '__main__':
    main()
