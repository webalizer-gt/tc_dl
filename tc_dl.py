# Ensure dependencies are checked before importing anything else
def check_dependencies():
    """Check if yt-dlp, requests and colorama libraries are available."""
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

    # Check for colorama
    try:
        import colorama  # noqa
    except ImportError:
        missing_dependencies.append("colorama")

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
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Default values
CONFIG_FILE = "config.json"
# Global configuration variable
config = {} 
# In-memory cache for game names
game_cache = {}

# Twitch API URLs
USER_API_URL = "https://api.twitch.tv/helix/users"
CLIPS_API_URL = "https://api.twitch.tv/helix/clips"
GAME_API_URL = "https://api.twitch.tv/helix/games"
VALIDATE_TOKEN_URL = "https://id.twitch.tv/oauth2/validate"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Twitch clip downloader.")
    parser.add_argument(
        "-c", action="store_true",
        help="Configure user defaults and Twitch credentials."
    )
    parser.add_argument(
        "-s", action="store_true",
        help="Start in simulation mode (does everything but download)."
    )
    return parser.parse_args()

def load_config():
    """Load configuration from config.json if it exists."""
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            try:
                config = json.load(file)
            except json.JSONDecodeError:
                print(f"{Fore.RED}Error: Unable to read {CONFIG_FILE}. Starting with an empty configuration.")
    else:
        print(f"{Fore.YELLOW}Warning: No configuration file found. Starting with an empty configuration.")
        config = {}
        input_defaults()

def get_downloads_path():
    """Get the default downloads path based on the operating system."""
    if platform.system() == "Windows":
        # For Windows, use the `USERPROFILE` environment variable
        downloads_path = os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:
        # For Linux and macOS, use the `HOME` environment variable
        downloads_path = os.path.join(os.environ['HOME'], 'Downloads')
    return downloads_path

def input_defaults():
    """Prompt the user for configuration values and save them to config.json."""
    user_config = get_user_config()
    old_default_user_name = user_config["default_user_name"]
    old_dl_folder = user_config["dl_folder"]
    old_spacer = user_config["spacer"]

    # Prompt for default Twitch user name
    default_user_name = input(f"Enter the default Twitch-User{' or press Enter to keep ' + old_default_user_name if old_default_user_name else ''}: ").strip() or old_default_user_name
    downloads_path = get_downloads_path()
    # Prompt for download folder path
    dl_folder = input(f"Enter the download folder path{' or press Enter to keep ' + old_dl_folder if old_dl_folder else ' or press Enter to use ' + downloads_path}: ").strip() or old_dl_folder or downloads_path
    # Prompt for spacer to use in file names
    spacer = input(f"Enter the spacer to use in file names{' or press Enter to keep ' + old_spacer if old_spacer else ''}: ") or old_spacer

    # Validate inputs
    if not dl_folder:
        print(f"{Fore.RED}Error: The download folder path cannot be empty.")
        return
    if not spacer:
        print(f"{Fore.RED}Error: The spacer cannot be empty.")
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

    client_id = input(f"Enter the Client ID{' or press Enter to keep ' + old_client_id if old_client_id else ''}: ").strip() or old_client_id
    client_secret = input(f"Enter the Client Secret{' or press Enter to keep ' + old_client_secret if old_client_secret else ''}: ").strip() or old_client_secret

    # Validate inputs
    if not client_id:
        print(f"{Fore.RED}Error: The Client ID cannot be empty.")
        return
    if not client_secret:
        print(f"{Fore.RED}Error: The Client Secret cannot be empty.")
        return

    # Save auth configuration
    save_config_section("auth", {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": auth_config.get("access_token", ""),
        "expires_at": auth_config.get("expires_at", "")
    })

def is_token_valid():
    """Check if the current OAuth token is still valid."""
    auth = config.get("auth", {})
    if "access_token" in auth and auth["access_token"] and "expires_at" in auth:
        try:
            expires_at = datetime.strptime(auth["expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() < expires_at:
                # Verify token with Twitch API
                headers = {"Authorization": f"Bearer {auth['access_token']}"}
                response = requests.get(VALIDATE_TOKEN_URL, headers=headers)
                if response.status_code == 200:
                    return True
                else:
                    print(f"{Fore.YELLOW}Info: Token is invalid or expired according to Twitch API.")
                    return False
        except ValueError:
            print(f"{Fore.RED}Error: Invalid date format in expires_at.")
            return False
    return False

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
    print(f"{Fore.GREEN}{section.capitalize()} configuration saved to {CONFIG_FILE}.")

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
        print(f"{Fore.RED}Error: Client ID or Client Secret not provided.")
        return None

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        token_data = response.json()

        if token_data:
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")
            expiration_date = datetime.now() + timedelta(seconds=expires_in)
            formatted_date = expiration_date.strftime("%Y-%m-%d %H:%M:%S")

            print(f"{Fore.GREEN}Token generated successfully. New access token: {access_token}, expires at: {formatted_date}")

            # Save auth configuration
            save_config_section("auth", {
                "client_id": client_id,
                "client_secret": client_secret,
                "access_token": access_token,
                "expires_at": formatted_date
            })
            return token_data

    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Error: Failed to generate token. {e}")

    return None

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
        "access_token": auth_config.get("access_token", ""),
        "expires_at": auth_config.get("expires_at", "")
    }

def input_channel_name():
    """Prompt for the Twitch channel name."""
    user_config = get_user_config()
    default_user_name = user_config["default_user_name"]
    user_name = input(f"Please enter the Twitch channel name (Default: {default_user_name}): ").strip()
    print()  # empty line
    return user_name or default_user_name

def get_broadcaster_id(user_name):
    """Get the broadcaster ID based on the channel name."""
    auth_config = get_auth_config()
    headers = {"Client-ID": auth_config["client_id"], "Authorization": f"Bearer {auth_config['access_token']}"}
    params = {"login": user_name}
    
    try:
        response = requests.get(USER_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            print(f"{Fore.RED}Error: User '{user_name}' not found.")
            exit(1)
        
        return data["data"][0]["id"]
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Error: Failed to fetch broadcaster ID for user '{user_name}'. {e}")
        return None

def input_time_range():
    """Prompt for the time range for clips."""
    start_date = input("Please enter the start date for the clips (YYYY-MM-DD): ").strip()
    end_date = input("Please enter the end date for the clips (YYYY-MM-DD): ").strip()
    print()  # empty line

    # Validate dates
    try:
        start_timestamp = datetime.fromisoformat(start_date).isoformat() + "Z"
        end_timestamp = (datetime.fromisoformat(end_date) + timedelta(days=1) - timedelta(seconds=1)).isoformat() + "Z"
    except ValueError:
        print(f"{Fore.RED}Error: Invalid date format. Please use YYYY-MM-DD.")
        exit(1)

    if start_timestamp > end_timestamp:
        print(f"{Fore.RED}Error: Start date cannot be after the end date.")
        exit(1)

    return start_timestamp, end_timestamp

def get_clips(broadcaster_id, start_timestamp, end_timestamp):
    """Fetch clips from the Twitch API."""
    auth_config = get_auth_config()
    headers = {"Client-ID": auth_config["client_id"], "Authorization": f"Bearer {auth_config['access_token']}"}
    clips = []
    seen_clip_ids = set()

    def fetch_clips(limit):
        params = {
            "broadcaster_id": broadcaster_id,
            "first": limit,
            "started_at": start_timestamp,
            "ended_at": end_timestamp,
        }
        cursor = None
        while True:
            try:
                if cursor:
                    params["after"] = cursor
                response = requests.get(CLIPS_API_URL, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                for clip in data.get("data", []):
                    if clip["id"] not in seen_clip_ids:
                        clips.append(clip)
                        seen_clip_ids.add(clip["id"])
                cursor = data.get("pagination", {}).get("cursor")
                
                if not cursor:
                    break
            except requests.exceptions.RequestException as e:
                print(f"{Fore.RED}Error: Failed to fetch clips. {e}")
                break

    # Fetch clips with different limits
    fetch_clips(2)
    fetch_clips(99)

    clips.sort(key=lambda x: x["created_at"])
    return clips

def get_game_name(game_id):
    """
    Fetch the name of a game based on its game_id, with in-memory caching.
    
    Args:
        game_id (str): The ID of the game.

    Returns:
        str: The name of the game or "Unknown" if an error occurs.
    """
    # Check the cache first
    if game_id in game_cache:
        return game_cache[game_id]

    # If not in cache, fetch from API
    auth_config = get_auth_config()
    headers = {"Client-ID": auth_config["client_id"], "Authorization": f"Bearer {auth_config['access_token']}"}
    params = {"id": game_id}

    try:
        response = requests.get(GAME_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            game_name = data["data"][0]["name"]
            game_cache[game_id] = game_name  # Save to in-memory cache
            return game_name
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Error: Failed to fetch game name for game_id {game_id}. {e}")
    
    return "Unknown"

def download_clips(clips, simulation_mode=False):
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
                print(f"{Fore.YELLOW}Warning: Skipping clip with missing data: {clip}")
                continue

            # Define the file name
            file_name = f"{clip_date}{spacer}{game_name}{spacer}{clip_title}{spacer}{clip_creator}.mp4"
            file_path = os.path.join(dl_folder, file_name)

            # Skip download if file already exists
            if os.path.exists(file_path):
                print(f"{Fore.YELLOW}Info: Skipping download, file already exists: {file_name}")
                downloaded_clips.append(file_path)
                continue

            if simulation_mode:
                print(f"{Fore.GREEN}Simulating download:{Fore.RESET} {file_name}")
                downloaded_clips.append(file_path)
                continue

            print(f"{Fore.GREEN}Downloading clip:{Fore.RESET} {file_name}")

            # Options for yt-dlp
            ydl_opts = {
                "outtmpl": file_path,  # File name template
                "quiet": True,         # Minimal output
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip_url])

            downloaded_clips.append(file_path)  # Add the file path to the list

        except Exception as e:
            print(f"{Fore.RED}Error: Failed to download {clip_url}. {e}")

    return downloaded_clips

def open_clips_in_vlc(clips):
    """
    Open a list of video clips in VLC media player.

    Args:
        clips (list): A list of file paths to open in VLC.
    """
    if not clips:
        print(f"{Fore.YELLOW}Info: No clips available to play.")
        return

    open_vlc = input("Would you like to open the downloaded clips in VLC? (y/N): ").strip().lower() or "n"
    if open_vlc != 'y':
        print(f"{Fore.YELLOW}Info: VLC will not be opened.")
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
            raise OSError(f"{Fore.RED}Error: Unsupported platform: {current_platform}")

        # Check if VLC is installed and accessible
        if not shutil.which(vlc_command[0]):
            raise FileNotFoundError(f"{Fore.RED}Error: {vlc_command[0]} is not installed or not in the PATH.")

        # Launch VLC
        subprocess.Popen(vlc_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"{Fore.GREEN}Info: VLC launched successfully.")
    except FileNotFoundError as fnf_error:
        print(f"{Fore.RED}Error: {fnf_error}")
    except OSError as os_error:
        print(f"{Fore.RED}Error: {os_error}")
    except Exception as ex:
        print(f"{Fore.RED}Error: An unexpected error occurred: {ex}")

def main():
    """Main program."""

    global config
    args = parse_arguments()
    
    # Load configuration file
    load_config()

    if args.c:
        # Run configuration prompt
        input_defaults()
        return

    # Check if token is valid, renew if necessary
    if not is_token_valid():
        print(f"{Fore.YELLOW}Info: Token is invalid or expired. Renewing token...")
        manage_twitch_oauth_token()

    print()  # empty line

    # Get information to download clips
    user_name = input_channel_name()
    broadcaster_id = get_broadcaster_id(user_name)
    start_timestamp, end_timestamp = input_time_range()

    print(f"Fetching clips for channel: {user_name}")
    clips = get_clips(broadcaster_id, start_timestamp, end_timestamp)

    if not clips:
        print("Info: No clips found.")
        return

    print(f"Info: {len(clips)} clips found. {Fore.GREEN}Starting download...")
    downloaded_clips = download_clips(clips, simulation_mode=args.s)
    print(f"{Fore.GREEN}Info: All clips have been downloaded.")

    # Launch VLC with the downloaded clips
    if downloaded_clips:
        open_clips_in_vlc(downloaded_clips)

if __name__ == "__main__":
    main()
