import os
import re
import requests
import datetime
import json
import argparse
from yt_dlp import YoutubeDL
from datetime import datetime, timedelta

# Default values
CONFIG_FILE = "config.json"
config = {}  # Global configuration variable

# Twitch API URLs
USER_API_URL = "https://api.twitch.tv/helix/users"
CLIPS_API_URL = "https://api.twitch.tv/helix/clips"
LIMIT = 100  # Max clips per request

def generate_twitch_oauth_token(client_id, client_secret):
    """
    Generates an OAuth token for Twitch.

    Args:
        client_id (str): The Client ID of the Twitch application.
        client_secret (str): The Client Secret of the Twitch application.

    Returns:
        dict: A dictionary with the access token and other information.
    """
    url = "https://id.twitch.tv/oauth2/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error generating token: {e}")
        return None

def load_config():
    """Load configuration from config.json if it exists."""
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            try:
                config = json.load(file)
            except json.JSONDecodeError:
                print(f"Error reading {CONFIG_FILE}. Starting with an empty configuration.")
    else:
        print(f"No configuration file found. Starting with an empty configuration.")
        config = {}
        save_defaults()

def get_user_config():
    """Extract user configuration from the loaded config."""
    user_config = config.get("user", {})
    return {
        "default_user_name": user_config.get("default_user_name", "default-channel"),
        "spacer": user_config.get("spacer", " ¦ "),
        "dl_folder": user_config.get("dl_folder", "")
    }

def get_auth_config():
    """Extract authentication configuration from the loaded config."""
    auth_config = config.get("auth", {})
    return {
        "client_id": auth_config.get("client_id", ""),
        "client_secret": auth_config.get("client_secret", ""),
        "oauth_token": auth_config.get("access_token", ""),
        "expires_at": auth_config.get("expires_at", "")
    }

def save_defaults():
    """Prompt the user for configuration values and save them to config.json."""
    user_config = get_user_config()
    old_default_user_name = user_config["default_user_name"]
    old_dl_folder = user_config["dl_folder"]
    old_spacer = user_config["spacer"]

    default_user_name = input(f"Enter the default Twitch-User or press Enter to keep {old_default_user_name}): ").strip() or old_default_user_name
    dl_folder = input(f"Enter the download folder path or press Enter to keep {old_dl_folder}): ").strip() or old_dl_folder
    spacer = input(f"Enter the spacer to use in file names or press Enter to keep '{old_spacer}'): ") or old_spacer

    # Prompt for Client ID and Client Secret
    auth_config = get_auth_config()
    old_client_id = auth_config["client_id"]
    old_client_secret = auth_config["client_secret"]
    old_access_token = auth_config["oauth_token"]
    old_expires_at = auth_config["expires_at"] 

    client_id = input(f"Enter the Client ID or press Enter to keep {old_client_id}: ").strip() or old_client_id
    client_secret = input(f"Enter the Client Secret or press Enter to keep {old_client_secret}: ").strip() or old_client_secret

    # Validate inputs
    if not dl_folder:
        print("Error: dl_folder cannot be empty.")
        return
    if not spacer:
        print("Error: spacer cannot be empty.")
        return
    if not client_id:
        print("Error: client_id cannot be empty.")
        return
    if not client_secret:
        print("Error: client_secret cannot be empty.")
        return

    # Update the "user" and "auth" sections
    config["user"] = {
        "default_user_name": default_user_name,
        "dl_folder": dl_folder,
        "spacer": spacer,
    }
    config["auth"] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": old_access_token,
        "expires_at": old_expires_at,
    }

    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)
    print(f"Configuration saved to {CONFIG_FILE}.")

def save_auth_config(client_id, client_secret, access_token, expires_at):
    """Save authentication configuration to config.json."""
    
    # Update only the "auth" section
    config["auth"] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": access_token,
        "expires_at": expires_at,
    }

    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)
    print(f"Authentication configuration saved to {CONFIG_FILE}.")

def is_token_valid():
    auth = config.get("auth", {})
    if "access_token" in auth and auth["access_token"] and "expires_at" in auth:
        try:
            expires_at = datetime.strptime(auth["expires_at"], "%Y-%m-%d %H:%M:%S")
            return datetime.now() < expires_at
        except ValueError:
            print("Invalid date format in expires_at.")
            return False
    return False

def renew_token():
    auth = config.get("auth", {})
    client_id = auth.get("client_id")
    client_secret = auth.get("client_secret")
    
    if not client_id or not client_secret:
        print("Client ID or Client Secret not found in configuration.")
        return

    token_data = generate_twitch_oauth_token(client_id, client_secret)

    if token_data:
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")
        expiration_date = datetime.now() + timedelta(seconds=expires_in)
        formatted_date = expiration_date.strftime("%Y-%m-%d %H:%M:%S")

        print(f"Token renewed. New access token: {access_token}, expires at: {formatted_date}")

        auth.update({
            "access_token": access_token,
            "expires_at": formatted_date,
        })
        config["auth"] = auth

        save_auth_config(client_id, client_secret, access_token, formatted_date)
    else:
        print("Error renewing token.")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Twitch clip downloader.")
    parser.add_argument(
        "-c", action="store_true",
        help="Configure default user name, download folder, and spacer."
    )
    return parser.parse_args()

def check_dependencies():
    """Check if yt-dlp is available."""
    try:
        import yt_dlp  # noqa
    except ImportError:
        print("Error: The library yt-dlp is not installed.")
        print("Please install it using: pip install yt-dlp")
        exit(1)

def get_channel_name():
    """Prompt for the Twitch channel name."""
    user_config = get_user_config()
    default_user_name = user_config["default_user_name"]
    user_name = input(f"Please enter the Twitch channel name (Default: {default_user_name}): ").strip()
    return user_name or default_user_name

def get_time_range():
    """Prompt for the time range for clips."""
    start_date = input("Please enter the start date for the clips (YYYY-MM-DD): ").strip()
    end_date = input("Please enter the end date for the clips (YYYY-MM-DD): ").strip()

    # Validate dates
    try:
        start_timestamp = datetime.fromisoformat(start_date).isoformat() + "Z"
        end_timestamp = datetime.fromisoformat(end_date).isoformat() + "Z"
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        exit(1)

    if start_timestamp > end_timestamp:
        print("Error: Start date is after the end date.")
        exit(1)

    return start_timestamp, end_timestamp

def get_broadcaster_id(user_name):
    """Get the broadcaster ID based on the channel name."""
    auth_config = get_auth_config()
    headers = {"Client-ID": auth_config["client_id"], "Authorization": f"Bearer {auth_config['oauth_token']}"}
    params = {"login": user_name}
    response = requests.get(USER_API_URL, headers=headers, params=params)

    if response.status_code != 200:
        print("Error fetching broadcaster ID:", response.json())
        exit(1)

    data = response.json()
    if not data.get("data"):
        print(f"Error: User {user_name} not found.")
        exit(1)

    return data["data"][0]["id"]

def get_clips(broadcaster_id, start_timestamp, end_timestamp):
    """Fetch clips from the Twitch API."""
    auth_config = get_auth_config()
    headers = {"Client-ID": auth_config["client_id"], "Authorization": f"Bearer {auth_config['oauth_token']}"}
    params = {
        "broadcaster_id": broadcaster_id,
        "first": LIMIT,
        "started_at": start_timestamp,
        "ended_at": end_timestamp,
    }
    clips = []
    cursor = None

    while True:
        if cursor:
            params["after"] = cursor
        response = requests.get(CLIPS_API_URL, headers=headers, params=params)

        if response.status_code != 200:
            print("Error fetching clips:", response.json())
            break

        data = response.json()
        clips.extend(data.get("data", []))
        cursor = data.get("pagination", {}).get("cursor")

        if not cursor:
            break

    return clips

def download_clips(clips):
    """Download clips using yt-dlp and format file names as specified."""
    user_config = get_user_config()
    spacer = user_config["spacer"]
    dl_folder = user_config["dl_folder"]
    for clip in clips:
        try:
            # Retrieve clip information
            clip_url = clip.get("url")
            clip_title = re.sub(r"[^\w\s]", "", clip.get("title", "untitled")).strip()
            clip_creator = re.sub(r"[^\w\s]", "", clip.get("creator_name", "unknown")).strip()
            clip_date = clip.get("created_at", "").split("T")[0]
            clip_game_id = clip.get("game_id", "0")

            # Check if essential data is present
            if not clip_url or not clip_date:
                print(f"Skipping clip with missing data: {clip}")
                continue

            # Define the file name
            file_name = f"{clip_game_id}{spacer}{clip_title}{spacer}{clip_creator}.mp4"

            print(f"Downloading clip: {clip_url} as {file_name}")

            # Options for yt-dlp
            ydl_opts = {
                "outtmpl": os.path.join(dl_folder, file_name),  # File name template
                "quiet": True,         # Minimal output
                # "format": "best",      # Best available quality
            }

            # Execute yt-dlp download
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip_url])
        except Exception as e:
            print(f"Error downloading {clip_url}: {e}")

def main():
    """Main program."""
    global config
    args = parse_arguments()
    
    # Load configuration file
    load_config()

    if args.c:
        # Run configuration prompt
        save_defaults()
        return

    check_dependencies()

    # Check if token is valid, renew if necessary
    if not is_token_valid():
        print("Token is invalid or expired. Renewing token...")
        renew_token()

    user_name = get_channel_name()
    broadcaster_id = get_broadcaster_id(user_name)
    start_timestamp, end_timestamp = get_time_range()

    print(f"Fetching clips for channel: {user_name}")
    clips = get_clips(broadcaster_id, start_timestamp, end_timestamp)

    if not clips:
        print("No clips found.")
        return

    print(f"{len(clips)} clips found. Starting download...")
    download_clips(clips)
    print("All clips have been downloaded.")

if __name__ == "__main__":
    main()
