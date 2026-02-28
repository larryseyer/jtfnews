#!/usr/bin/env python3
"""Test the daily digest pipeline end-to-end.

This script provides utilities to test individual components of the digest
pipeline as well as the full end-to-end flow.

Usage:
    python test_digest.py --stories --date 2026-02-22  # Test story loading
    python test_digest.py --obs                         # Test OBS connection
    python test_digest.py --youtube                     # Test YouTube auth
    python test_digest.py --full --date 2026-02-22      # Full digest test
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from main import (
    load_stories_for_date,
    generate_and_upload_daily_summary,
    get_obs_connection,
    upload_to_youtube,
    get_authenticated_youtube_service,
    BASE_DIR,
    DATA_DIR,
)


def test_story_loading(date: str) -> bool:
    """Test loading stories from local or archive.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        True if stories were loaded successfully, False otherwise
    """
    print(f"\n=== Testing Story Loading for {date} ===")

    # Check what files exist
    local_file = DATA_DIR / f"{date}.txt"
    year = date[:4]
    archive_file = BASE_DIR / "gh-pages-dist" / "archive" / year / f"{date}.txt.gz"

    print(f"Local file: {local_file}")
    print(f"  Exists: {local_file.exists()}")

    print(f"Archive file: {archive_file}")
    print(f"  Exists: {archive_file.exists()}")

    # Load stories
    stories = load_stories_for_date(date)
    print(f"\nLoaded {len(stories)} stories")

    if stories:
        print("\nFirst 3 stories:")
        for i, s in enumerate(stories[:3]):
            fact_preview = s['fact'][:60] + "..." if len(s['fact']) > 60 else s['fact']
            print(f"  {i+1}. [{s.get('source', 'Unknown')}] {fact_preview}")
            if s.get('audio'):
                print(f"      Audio: {s['audio']}")

        # Count stories with audio
        with_audio = sum(1 for s in stories if s.get('audio'))
        print(f"\nStories with audio: {with_audio}/{len(stories)}")

        return True
    else:
        print("No stories found!")
        return False


def test_obs_connection() -> bool:
    """Test OBS WebSocket connection.

    Returns:
        True if connection successful, False otherwise
    """
    print("\n=== Testing OBS Connection ===")

    try:
        ws = get_obs_connection()
        if ws:
            print("OBS connection: OK")

            # Try to get some info
            try:
                from obswebsocket import requests as obs_requests
                # Get current scene
                response = ws.call(obs_requests.GetCurrentScene())
                current_scene = response.datain.get('name', 'Unknown')
                print(f"Current scene: {current_scene}")

                # Get recording status
                rec_status = ws.call(obs_requests.GetRecordingStatus())
                is_recording = rec_status.datain.get('isRecording', False)
                print(f"Recording: {'Yes' if is_recording else 'No'}")

            except Exception as e:
                print(f"Warning: Could not get OBS status: {e}")

            ws.disconnect()
            print("Disconnected from OBS")
            return True
        else:
            print("OBS connection: FAILED - get_obs_connection() returned None")
            return False

    except Exception as e:
        print(f"OBS connection: FAILED - {e}")
        return False


def test_youtube_auth() -> bool:
    """Test YouTube API authentication.

    Returns:
        True if authentication successful, False otherwise
    """
    print("\n=== Testing YouTube Authentication ===")

    try:
        service = get_authenticated_youtube_service()
        if service:
            print("YouTube auth: OK")

            # Try to get channel info to verify the auth works
            try:
                request = service.channels().list(
                    part="snippet",
                    mine=True
                )
                response = request.execute()
                if response.get('items'):
                    channel = response['items'][0]['snippet']
                    print(f"Channel: {channel.get('title', 'Unknown')}")
            except Exception as e:
                print(f"Warning: Could not get channel info: {e}")

            return True
        else:
            print("YouTube auth: FAILED - get_authenticated_youtube_service() returned None")
            return False

    except Exception as e:
        print(f"YouTube auth: FAILED - {e}")
        return False


def test_full_digest(date: str, upload: bool = False) -> bool:
    """Run the full digest pipeline.

    Args:
        date: Date string in YYYY-MM-DD format
        upload: Whether to upload to YouTube (default: False)

    Returns:
        True if digest completed successfully, False otherwise
    """
    print(f"\n=== Full Digest Test for {date} ===")

    if not upload:
        print("NOTE: Upload is disabled. Video will be generated but not uploaded.")
        print("      Use --upload flag to enable YouTube upload.")

    # First verify we have stories
    stories = load_stories_for_date(date)
    if not stories:
        print(f"ERROR: No stories found for {date}. Cannot generate digest.")
        return False

    print(f"Found {len(stories)} stories for {date}")

    # Run the full digest
    try:
        generate_and_upload_daily_summary(date)

        # Check if video was created
        video_path = BASE_DIR / "video" / f"{date}-daily-digest.mp4"
        if video_path.exists():
            size_mb = video_path.stat().st_size / (1024 * 1024)
            print(f"\nVideo created: {video_path}")
            print(f"Size: {size_mb:.1f} MB")
            return True
        else:
            print(f"\nWARNING: Video file not found at {video_path}")
            return False

    except Exception as e:
        print(f"ERROR during digest generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_available_dates():
    """List dates that have archived stories available."""
    print("\n=== Available Archived Dates ===")

    archive_dir = BASE_DIR / "gh-pages-dist" / "archive"
    if not archive_dir.exists():
        print(f"Archive directory not found: {archive_dir}")
        return

    available = []
    for year_dir in sorted(archive_dir.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            for gz_file in sorted(year_dir.glob("*.txt.gz")):
                date = gz_file.stem.replace(".txt", "")
                available.append(date)

    if available:
        print(f"Found {len(available)} archived dates:")
        for date in available[-10:]:  # Show last 10
            print(f"  {date}")
        if len(available) > 10:
            print(f"  ... and {len(available) - 10} more")
    else:
        print("No archived dates found")


def main():
    parser = argparse.ArgumentParser(
        description="Test daily digest pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_digest.py --stories --date 2026-02-22
    python test_digest.py --obs
    python test_digest.py --youtube
    python test_digest.py --full --date 2026-02-22
    python test_digest.py --list
        """
    )
    parser.add_argument("--date", help="Date to test (YYYY-MM-DD)")
    parser.add_argument("--stories", action="store_true", help="Test story loading")
    parser.add_argument("--obs", action="store_true", help="Test OBS connection")
    parser.add_argument("--youtube", action="store_true", help="Test YouTube auth")
    parser.add_argument("--full", action="store_true", help="Run full digest")
    parser.add_argument("--upload", action="store_true", help="Actually upload to YouTube")
    parser.add_argument("--list", action="store_true", help="List available archived dates")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    results = {}

    if args.list:
        list_available_dates()
        return

    if args.stories or args.all:
        date = args.date or "2026-02-22"
        results['stories'] = test_story_loading(date)

    if args.obs or args.all:
        results['obs'] = test_obs_connection()

    if args.youtube or args.all:
        results['youtube'] = test_youtube_auth()

    if args.full:
        date = args.date or "2026-02-24"
        results['full'] = test_full_digest(date, args.upload)

    # Print summary
    if results:
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        for test, passed in results.items():
            status = "PASS" if passed else "FAIL"
            print(f"  {test}: {status}")


if __name__ == "__main__":
    main()
