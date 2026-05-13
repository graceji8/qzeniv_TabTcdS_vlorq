"""
generate_token.py — Run this ONCE locally to create token.pickle via OAuth2.

Usage:
    1. Place your OAuth2 Client credentials file as credentials.json in the repo root
       (or pass --credentials path/to/credentials.json)
    2. Run:  python scripts/generate_token.py
    3. A browser window will open. Sign in and grant access.
    4. token.pickle is saved in the repo root.
    5. Base64-encode it and add as GOOGLE_DRIVE_TOKEN secret in GitHub:
         python -c "import base64; print(base64.b64encode(open('token.pickle','rb').read()).decode())"
       Copy that output into GitHub → Settings → Secrets → GOOGLE_DRIVE_TOKEN
"""

import os
import sys
import pickle
import base64
import argparse
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
]

def main():
    parser = argparse.ArgumentParser(description='Generate token.pickle for Google Drive OAuth2')
    parser.add_argument('--credentials', default='credentials.json',
                        help='Path to OAuth2 client secrets JSON (default: credentials.json)')
    parser.add_argument('--token', default='token.pickle',
                        help='Output path for token.pickle (default: token.pickle)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for the local OAuth callback server (default: 8080)')
    parser.add_argument('--show-base64', action='store_true',
                        help='Print base64-encoded token for use as a GitHub secret')
    args = parser.parse_args()

    creds = None

    # Check for existing token
    if os.path.exists(args.token):
        with open(args.token, 'rb') as f:
            try:
                creds = pickle.load(f)
            except Exception:
                creds = None

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        print("Refreshing expired token...")
        creds.refresh(Request())
    elif not creds or not creds.valid:
        # Run the full OAuth2 flow
        if not os.path.exists(args.credentials):
            print(f"ERROR: {args.credentials} not found!")
            print()
            print("To get credentials.json:")
            print("  1. Go to https://console.cloud.google.com/apis/credentials")
            print("  2. Create an OAuth 2.0 Client ID (type: Desktop App)")
            print("  3. Download the JSON and save it as credentials.json")
            sys.exit(1)

        print(f"Starting OAuth2 flow using {args.credentials}...")
        print(f"A browser will open. Sign in with your Google account and grant access.")
        print()

        flow = InstalledAppFlow.from_client_secrets_file(args.credentials, SCOPES)
        creds = flow.run_local_server(port=args.port)

    # Save the token
    with open(args.token, 'wb') as f:
        pickle.dump(creds, f)
    print(f"✅ Token saved to {args.token}")

    # Show base64 for GitHub secret
    if args.show_base64:
        with open(args.token, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        print()
        print("=" * 60)
        print("BASE64-ENCODED TOKEN (copy this into GitHub Secrets")
        print("as GOOGLE_DRIVE_TOKEN):")
        print("=" * 60)
        print(encoded)
        print("=" * 60)
    else:
        print()
        print("To get the base64 string for GitHub Secrets, run:")
        print(f'  python scripts/generate_token.py --show-base64')
        print()
        print("Or manually:")
        print(f'  python -c "import base64; print(base64.b64encode(open(\'{args.token}\',\'rb\').read()).decode())"')

if __name__ == '__main__':
    main()
