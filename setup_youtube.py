#!/usr/bin/env python3
"""
YouTube OAuth Setup for JTF News Daily Video Uploads
=====================================================

This script guides you through setting up YouTube API credentials
for automatic daily summary video uploads.

Run this script once on any machine that will upload videos.
"""

import os
import sys
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]


def print_header(text):
    """Print a formatted header."""
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)
    print()


def print_step(number, text):
    """Print a numbered step."""
    print(f"\n[Step {number}] {text}")
    print("-" * 40)


def wait_for_enter(prompt="Press Enter to continue..."):
    """Wait for user to press Enter."""
    input(f"\n{prompt}")


def check_dependencies():
    """Check if required packages are installed."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        return True
    except ImportError:
        print("Required packages not installed.")
        print("Run: pip install google-api-python-client google-auth-oauthlib")
        return False


def find_client_secrets():
    """Look for existing client_secrets.json file."""
    possible_names = [
        "client_secrets.json",
        "client_secret.json",
        "credentials.json"
    ]

    for name in possible_names:
        path = BASE_DIR / name
        if path.exists():
            return path

    return None


def setup_google_cloud():
    """Guide user through Google Cloud Console setup."""
    print_header("Google Cloud Console Setup")

    print("""
To upload videos to YouTube, you need OAuth 2.0 credentials from Google Cloud.

If you already have a client_secrets.json file, place it in the project root
and press Enter.

Otherwise, follow these steps to create one:

1. Go to: https://console.cloud.google.com/

2. Create a new project (or select existing one)
   - Click the project dropdown at the top
   - Click "NEW PROJECT"
   - Name it something like "JTF News"
   - Click "CREATE"

3. Enable the YouTube Data API v3:
   - Go to: https://console.cloud.google.com/apis/library
   - Search for "YouTube Data API v3"
   - Click it, then click "ENABLE"

4. Create OAuth credentials:
   - Go to: https://console.cloud.google.com/apis/credentials
   - Click "CREATE CREDENTIALS" > "OAuth client ID"
   - If prompted, configure OAuth consent screen first:
     * User Type: External
     * App name: "JTF News"
     * User support email: your email
     * Developer contact: your email
     * Skip adding scopes (we'll specify them in code)
     * Add yourself as a test user
     * Save and continue
   - Back on credentials page, click "CREATE CREDENTIALS" > "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "JTF News Daily Videos"
   - Click "CREATE"

5. Download credentials:
   - Click the download icon next to your new credential
   - Save the file as "client_secrets.json" in this project folder:
     {base_dir}
""".format(base_dir=BASE_DIR))

    wait_for_enter("Press Enter when you've placed client_secrets.json in the project folder...")

    secrets_file = find_client_secrets()
    if not secrets_file:
        print("\nERROR: Could not find client_secrets.json")
        print(f"Please ensure the file is in: {BASE_DIR}")
        return None

    print(f"\nFound credentials file: {secrets_file}")
    return secrets_file


def authenticate(client_secrets_file):
    """Run OAuth flow to get user credentials."""
    print_header("YouTube Authentication")

    print("""
Now we'll authenticate with your Google/YouTube account.

A browser window will open asking you to sign in and grant permissions.
After you approve, the credentials will be saved locally for future use.
""")

    wait_for_enter()

    from google_auth_oauthlib.flow import InstalledAppFlow

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_file),
            SCOPES
        )

        # Run local server for OAuth callback
        creds = flow.run_local_server(port=8080)

        # Save credentials
        token_file = DATA_DIR / "youtube_tokens.json"
        DATA_DIR.mkdir(exist_ok=True)

        with open(token_file, 'w') as f:
            f.write(creds.to_json())

        print(f"\nCredentials saved to: {token_file}")
        return creds

    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        return None


def setup_playlist(creds):
    """Create or find Daily Summary playlist."""
    print_header("Playlist Setup")

    from googleapiclient.discovery import build

    youtube = build('youtube', 'v3', credentials=creds)

    # Check for existing "Daily Summary" playlist
    print("Checking for existing 'Daily Summary' playlist...")

    try:
        playlists = youtube.playlists().list(
            part='snippet',
            mine=True,
            maxResults=50
        ).execute()

        for playlist in playlists.get('items', []):
            title_lower = playlist['snippet']['title'].lower()
            if 'daily digest' in title_lower or 'daily summary' in title_lower:
                playlist_id = playlist['id']
                print(f"\nFound existing playlist: {playlist['snippet']['title']}")
                print(f"Playlist ID: {playlist_id}")
                return playlist_id

        # Create new playlist
        print("\nNo 'Daily Digest' playlist found. Creating one...")

        new_playlist = youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': 'JTF News - Daily Digest',
                    'description': 'Daily digest of verified facts from JTF News.\n'
                                  'No opinions. No adjectives. Just the facts.\n\n'
                                  'https://jtfnews.org/'
                },
                'status': {
                    'privacyStatus': 'public'
                }
            }
        ).execute()

        playlist_id = new_playlist['id']
        print(f"\nCreated playlist: {new_playlist['snippet']['title']}")
        print(f"Playlist ID: {playlist_id}")
        return playlist_id

    except Exception as e:
        print(f"\nFailed to setup playlist: {e}")
        print("You can manually create a playlist and add the ID to .env")
        return None


def update_env_file(client_secrets_filename, playlist_id):
    """Update .env file with YouTube configuration."""
    print_header("Environment Configuration")

    new_lines = [
        f"\n# YouTube Daily Video Configuration",
        f"YOUTUBE_CLIENT_SECRETS_FILE={client_secrets_filename}",
    ]

    if playlist_id:
        new_lines.append(f"YOUTUBE_PLAYLIST_ID={playlist_id}")

    # Check if .env exists and update
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            content = f.read()

        # Check if YouTube config already exists
        if 'YOUTUBE_CLIENT_SECRETS_FILE' in content:
            print("YouTube configuration already exists in .env")
            print("Please update manually if needed:")
            for line in new_lines[1:]:  # Skip comment
                print(f"  {line}")
            return

        with open(ENV_FILE, 'a') as f:
            f.write('\n'.join(new_lines) + '\n')
    else:
        print(f"WARNING: .env file not found at {ENV_FILE}")
        print("Add these lines to your .env file:")
        for line in new_lines:
            print(f"  {line}")
        return

    print(f"Updated {ENV_FILE} with YouTube configuration")


def verify_setup(creds):
    """Verify YouTube API access works."""
    print_header("Verification")

    from googleapiclient.discovery import build

    print("Testing YouTube API access...")

    try:
        youtube = build('youtube', 'v3', credentials=creds)

        # Get channel info
        channels = youtube.channels().list(
            part='snippet',
            mine=True
        ).execute()

        if channels.get('items'):
            channel = channels['items'][0]
            print(f"\nConnected to YouTube channel: {channel['snippet']['title']}")
            print("Setup successful!")
            return True
        else:
            print("\nWARNING: Could not find YouTube channel")
            print("Make sure you're using a Google account with a YouTube channel")
            return False

    except Exception as e:
        print(f"\nVerification failed: {e}")
        return False


def main():
    """Main setup flow."""
    print_header("JTF News - YouTube Setup")

    print("""
This script will guide you through setting up YouTube API access
for automatic daily summary video uploads.

You will need:
- A Google Cloud account (free)
- A YouTube channel where videos will be uploaded

The setup takes about 5-10 minutes.
""")

    wait_for_enter()

    # Check dependencies
    print_step(1, "Checking dependencies")
    if not check_dependencies():
        sys.exit(1)
    print("All dependencies installed.")

    # Find or setup client secrets
    print_step(2, "Setting up Google Cloud credentials")
    secrets_file = find_client_secrets()
    if secrets_file:
        print(f"Found existing credentials: {secrets_file}")
    else:
        secrets_file = setup_google_cloud()
        if not secrets_file:
            sys.exit(1)

    # Authenticate
    print_step(3, "Authenticating with YouTube")
    creds = authenticate(secrets_file)
    if not creds:
        sys.exit(1)

    # Setup playlist
    print_step(4, "Setting up Daily Summary playlist")
    playlist_id = setup_playlist(creds)

    # Update .env
    print_step(5, "Updating configuration")
    update_env_file(secrets_file.name, playlist_id)

    # Verify
    print_step(6, "Verifying setup")
    verify_setup(creds)

    print_header("Setup Complete!")

    print("""
Your YouTube integration is now configured.

Daily summary videos will be automatically:
- Generated at midnight GMT
- Uploaded to your YouTube channel
- Added to the "Daily Summary" playlist

To test manually, you can run:
  python -c "from main import generate_and_upload_daily_summary; generate_and_upload_daily_summary('2026-02-17')"

(Replace the date with a day that has archived stories/audio)

For more information, see:
  docs/plans/2026-02-18-DailyDigestUpgrade-design.md
""")


if __name__ == "__main__":
    main()
