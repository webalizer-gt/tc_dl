# Ensure dependencies are checked before importing anything else
def check_dependencies():
    """Check if yt-dlp and requests libraries are available."""
    missing_dependencies = []

    # Check for yt-dlp
    try:
        import yt_dlp  # noqa
    except ImportError:
        missing_dependencies.append("yt-dlp")

    # Check for requests
    try:
        import requests  # noqa
    except ImportError:
        missing_dependencies.append("requests")

    # If any dependencies are missing, notify the user and exit
    if missing_dependencies:
        print(f"Error: The following dependencies are missing: {', '.join(missing_dependencies)}")
        print("Please install them using:")
        print("    pip install " + " ".join(missing_dependencies))
        exit(1)

# Call the dependency check first
check_dependencies()

# Now import the required modules, since we've confirmed they're installed
import requests
from yt_dlp import YoutubeDL
import os
import platform
import re
import json
import argparse
from datetime import datetime, timedelta
import subprocess
import shutil

# Default values
CONFIG_FILE = "config.json"
config = {}  # Global configuration variable

# Twitch API URLs
USER_API_URL = "https://api.twitch.tv/helix/users"
CLIPS_API_URL = "https://api.twitch.tv/helix/clips"
GAME_API_URL = "https://api.twitch.tv/helix/games"
LIMIT = 10  # Max clips per request

def get_downloads_path():
    if platform.system() == "Windows":
        # For Windows, use the `USERPROFILE` environment variable
        downloads_path = os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:
        # For Linux and macOS, use the `HOME` environment variable
        downloads_path = os.path.join(os.environ['HOME'], 'Downloads')
    return downloads_path

def get_game_name(game_id):
    """
    Fetch the name of a game based on its game_id.
    
    Args:
        game_id (str): The ID of the game.

    Returns:
        str: The name of the game or "Unknown" if an error occurs.
    """
    auth_config = get_auth_config()
    headers = {"Client-ID": auth_config["client_id"], "Authorization": f"Bearer {auth_config['oauth_token']}"}
    params = {"id": game_id}

    try:
        response = requests.get(GAME_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]["name"]  # The name of the game
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game name for game_id {game_id}: {e}")
    
    return "Unknown"

def manage_twitch_oauth_token(client_id=None, client_secret=None):
    """
    Generates or renews a Twitch OAuth token using the client_credentials grant type.

    Args:
        client_id (str, optional): The Client ID of the Twitch application. Defaults to None.
        client_secret (str, optional): The Client Secret of the Twitch application. Defaults to None.

    Returns:
        dict: A dictionary with the access token and other information, or None if an error occurred.
    """
    auth = get_auth_config()
    client_id = client_id or auth.get("client_id")
    client_secret = client_secret or auth.get("client_secret")

    if not client_id or not client_secret:
        print("Client ID or Client Secret not provided.")
        return None

    url = "https://id.twitch.tv/oauth2/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()

        if token_data:
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")
            expiration_date = datetime.now() + timedelta(seconds=expires_in)
            formatted_date = expiration_date.strftime("%Y-%m-%d %H:%M:%S")

            print(f"Token generated. New access token: {access_token}, expires at: {formatted_date}")

            # Save auth configuration
            save_config_section("auth", {
                "client_id": client_id,
                "client_secret": client_secret,
                "access_token": access_token,
                "expires_at": formatted_date
            })
            return token_data

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
        get_defaults()

def get_user_config():
    """Extract user configuration from the loaded config."""
    user_config = config.get("user", {})
    return {
        "default_user_name": user_config.get("default_user_name"),
        "spacer": user_config.get("spacer", " ¦ "),
        "dl_folder": user_config.get("dl_folder")
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

def get_defaults():
    """Prompt the user for configuration values and save them to config.json."""
    user_config = get_user_config()
    old_default_user_name = user_config["default_user_name"]
    old_dl_folder = user_config["dl_folder"]
    old_spacer = user_config["spacer"]

    if not old_default_user_name:
        default_user_name = input(f"Enter the default Twitch-User: ").strip()
    else:
        default_user_name = input(f"Enter the default Twitch-User or press Enter to keep '{old_default_user_name}': ").strip() or old_default_user_name

    if not old_dl_folder:
        downloads_path = get_downloads_path()
        dl_folder = input(f"Enter the download folder path or press Enter to use '{downloads_path}': ").strip() or downloads_path
    else:
        dl_folder = input(f"Enter the download folder path or press Enter to keep '{old_dl_folder}': ").strip() or old_dl_folder
    
    if not old_spacer:
        spacer = input(f"Enter the spacer to use in file names: ")
    else:
        spacer = input(f"Enter the spacer to use in file names or press Enter to keep '{old_spacer}': ") or old_spacer

    # Validate inputs
    if not dl_folder:
        print("Error: dl_folder cannot be empty.")
        return
    if not spacer:
        print("Error: spacer cannot be empty.")
        return

    # Save user configuration
    save_config_section("user", {
        "default_user_name": default_user_name,
        "dl_folder": dl_folder,
        "spacer": spacer
    })

    # Prompt for Client ID and Client Secret
    auth_config = get_auth_config()
    old_client_id = auth_config["client_id"]
    old_client_secret = auth_config["client_secret"]
    old_access_token = auth_config["oauth_token"]
    old_expires_at = auth_config["expires_at"] 

    if not old_client_id:
        client_id = input(f"Enter the Client ID: ").strip()
    else:
        client_id = input(f"Enter the Client ID or press Enter to keep {old_client_id}: ").strip() or old_client_id

    if not old_client_secret:
        client_secret = input(f"Enter the Client Secret: ").strip()
    else:
        client_secret = input(f"Enter the Client Secret or press Enter to keep {old_client_secret}: ").strip() or old_client_secret

    # Validate inputs
    if not client_id:
        print("Error: client_id cannot be empty.")
        return
    if not client_secret:
        print("Error: client_secret cannot be empty.")
        return

    # Save auth configuration
    save_config_section("auth", {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": auth_config.get("oauth_token", ""),
        "expires_at": auth_config.get("expires_at", "")
    })

def save_config_section(section, data):
    """
    Save updates to a specific section of the configuration dictionary.
    
    Args:
        section (str): The section of the config to update (e.g., "user" or "auth").
        data (dict): The new data to save in the specified section.
    """
    if section not in config:
        config[section] = {}

    # Update the section with new data
    config[section].update(data)

    # Save to the config file
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)
    print(f"{section.capitalize()} configuration saved to {CONFIG_FILE}.")

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

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Twitch clip downloader.")
    parser.add_argument(
        "-c", action="store_true",
        help="Configure user defaults and Twitch credentials."
    )
    return parser.parse_args()

def get_channel_name():
    """Prompt for the Twitch channel name."""
    user_config = get_user_config()
    default_user_name = user_config["default_user_name"]
    user_name = input(f"Please enter the Twitch channel name (Default: {default_user_name}): ").strip()
    print()  # empty line
    return user_name or default_user_name

def get_time_range():
    """Prompt for the time range for clips."""
    start_date = input("Please enter the start date for the clips (YYYY-MM-DD): ").strip()
    end_date = input("Please enter the end date for the clips (YYYY-MM-DD): ").strip()
    print()  # empty line

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
    
    try:
        response = requests.get(USER_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            print(f"Error: User {user_name} not found.")
            return None
        
        return data["data"][0]["id"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching broadcaster ID for user {user_name}: {e}")
        return None


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
        try:
            if cursor:
                params["after"] = cursor
            response = requests.get(CLIPS_API_URL, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            clips.extend(data.get("data", []))
            cursor = data.get("pagination", {}).get("cursor")
            
            if not cursor:
                break
        except requests.exceptions.RequestException as e:
            print(f"Error fetching clips: {e}")
            break

    return clips


def download_clips(clips):
    """Download clips using yt-dlp and format file names as specified."""
    user_config = get_user_config()
    spacer = user_config["spacer"]
    dl_folder = user_config["dl_folder"]
    downloaded_clips = []  # List to store paths of downloaded clips

    for clip in clips:
        try:
            # Retrieve clip information
            broadcaster_name = re.sub(r"[^\w\s]", "", clip.get("broadcaster_name", "unknown")).strip()
            clip_url = clip.get("url")
            clip_title = re.sub(r"[^\w\s]", "", clip.get("title", "untitled")).strip()
            clip_creator = re.sub(r"[^\w\s]", "", clip.get("creator_name", "unknown")).strip()
            clip_date = clip.get("created_at", "").split("T")[0]
            game_id = clip.get("game_id", "0")
            game_name = re.sub(r"[^\w\s]", "", get_game_name(game_id)).strip()  # Fetch the game name

            if not clip_url or not clip_date:
                print(f"Skipping clip with missing data: {clip}")
                continue

            # Define the file name
            file_name = f"{game_name}{spacer}{clip_title}{spacer}{clip_creator}.mp4"
            file_path = os.path.join(dl_folder, file_name)

            # Skip download if file already exists
            if os.path.exists(file_path):
                print(f"Skipping download, file already exists: {file_name}")
                downloaded_clips.append(file_path)
                continue
            print(f"Downloading clip: {clip_url} as {file_name}")

            # Options for yt-dlp
            ydl_opts = {
                "outtmpl": file_path,  # File name template
                "quiet": True,         # Minimal output
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip_url])

            downloaded_clips.append(file_path)  # Add the file path to the list

        except Exception as e:
            print(f"Error downloading {clip_url}: {e}")

    return downloaded_clips

def open_clips_in_vlc(clips):
    """
    Open a list of video clips in VLC media player.

    Args:
        clips (list): A list of file paths to open in VLC.
    """
    if not clips:
        print("No clips available to play.")
        return

    open_vlc = input("Would you like to open the downloaded clips in VLC? (y/n): ").strip().lower()
    if open_vlc != 'y':
        print("VLC will not be opened.")
        return

    # Determine the platform
    current_platform = platform.system()

    # Command to launch VLC
    try:
        if current_platform == "Windows":
            # Windows-specific VLC command
            vlc_command = [r"C:\Program Files\VideoLAN\VLC\vlc.exe", *clips]
        elif current_platform in ("Linux", "Darwin"):  # Darwin is macOS
            # Linux/macOS-specific VLC command
            vlc_command = ["vlc", *clips]
        else:
            raise OSError(f"Unsupported platform: {current_platform}")

        # Check if VLC is installed and accessible
        if not shutil.which(vlc_command[0]):
            raise FileNotFoundError(f"{vlc_command[0]} is not installed or not in the PATH.")

        # Launch VLC
        subprocess.Popen(vlc_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print("VLC launched successfully.")
    except FileNotFoundError as fnf_error:
        print(f"Error: {fnf_error}")
    except OSError as os_error:
        print(f"Error: {os_error}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")


def main():
    """Main program."""

    global config
    args = parse_arguments()
    
    # Load configuration file
    load_config()

    if args.c:
        # Run configuration prompt
        get_defaults()
        return

    # Check if token is valid, renew if necessary
    if not is_token_valid():
        print("Token is invalid or expired. Renewing token...")
        manage_twitch_oauth_token()

    print()  # empty line

    # Get information to download clips
    user_name = get_channel_name()
    broadcaster_id = get_broadcaster_id(user_name)
    start_timestamp, end_timestamp = get_time_range()

    print(f"Fetching clips for channel: {user_name}")
    clips = get_clips(broadcaster_id, start_timestamp, end_timestamp)

    if not clips:
        print("No clips found.")
        return

    print(f"{len(clips)} clips found. Starting download...")
    downloaded_clips = download_clips(clips)
    print("All clips have been downloaded.")

    # Launch VLC with the downloaded clips
    if downloaded_clips:
        open_clips_in_vlc(downloaded_clips)

if __name__ == "__main__":
    main()
