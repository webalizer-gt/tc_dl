import os
import re
import requests
import datetime
from yt_dlp import YoutubeDL

# Benutzereingaben (ersetzen mit deinen eigenen Werten)
CLIENT_ID = "client-id"  # Deine Twitch Client-ID
OAUTH_TOKEN = "outh-token"  # Dein OAuth Token
DEFAULT_USER_NAME = "standard-kanal" # Standard-Kanal
SPACER = " ¦ "  # Trennzeichen für Dateinamen

# Twitch API URLs
USER_API_URL = "https://api.twitch.tv/helix/users"
CLIPS_API_URL = "https://api.twitch.tv/helix/clips"
LIMIT = 100  # Max Clips pro Anfrage

def check_dependencies():
    """Prüfen, ob yt-dlp verfügbar ist."""
    try:
        import yt_dlp  # noqa
    except ImportError:
        print("Fehler: Die Bibliothek yt-dlp ist nicht installiert.")
        print("Bitte installieren Sie sie mit: pip install yt-dlp")
        exit(1)

def get_channel_name():
    """Fragt den Twitch-Kanalnamen ab."""
    user_name = input(f"Bitte gib den Twitch-Kanalnamen ein (Standard: {DEFAULT_USER_NAME} ALLA!): ").strip()
    return user_name or DEFAULT_USER_NAME

def get_time_range():
    """Fragt den Zeitbereich für Clips ab."""
    start_date = input("Bitte gib das Startdatum für die Clips ein (YYYY-MM-DD): ").strip()
    end_date = input("Bitte gib das Enddatum für die Clips ein (YYYY-MM-DD): ").strip()

    # Datum validieren
    try:
        start_timestamp = datetime.datetime.fromisoformat(start_date).isoformat() + "Z"
        end_timestamp = datetime.datetime.fromisoformat(end_date).isoformat() + "Z"
    except ValueError:
        print("Ungültiges Datumformat. Bitte verwenden Sie YYYY-MM-DD.")
        exit(1)

    if start_timestamp > end_timestamp:
        print("Fehler: Startdatum liegt nach dem Enddatum.")
        exit(1)

    return start_timestamp, end_timestamp

def get_broadcaster_id(user_name):
    """Ermittelt die Broadcaster-ID basierend auf dem Kanalnamen."""
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {OAUTH_TOKEN}"}
    params = {"login": user_name}
    response = requests.get(USER_API_URL, headers=headers, params=params)

    if response.status_code != 200:
        print("Fehler beim Abrufen der Broadcaster-ID:", response.json())
        exit(1)

    data = response.json()
    if not data.get("data"):
        print(f"Fehler: Benutzer {user_name} nicht gefunden.")
        exit(1)

    return data["data"][0]["id"]

def get_clips(broadcaster_id, start_timestamp, end_timestamp):
    """Ruft Clips aus der Twitch API ab."""
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {OAUTH_TOKEN}"}
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
            print("Fehler beim Abrufen der Clips:", response.json())
            break

        data = response.json()
        clips.extend(data.get("data", []))
        cursor = data.get("pagination", {}).get("cursor")

        if not cursor:
            break

    return clips

def download_clips(clips):
    """Lädt Clips mit yt-dlp herunter und formatiert die Dateinamen gemäß den Vorgaben."""
    for clip in clips:
        try:
            # Clip-Informationen abrufen
            clip_url = clip.get("url")
            clip_title = re.sub(r"[^\w\s]", "", clip.get("title", "untitled")).strip()
            clip_creator = re.sub(r"[^\w\s]", "", clip.get("creator_name", "unknown")).strip()
            clip_date = clip.get("created_at", "").split("T")[0]

            # Überprüfen, ob wichtige Daten vorhanden sind
            if not clip_url or not clip_date:
                print(f"Überspringe Clip mit fehlenden Daten: {clip}")
                continue

            # Definiere den Dateinamen
            file_name = f"{clip_date}{SPACER}{clip_title}{SPACER}{clip_creator}.mp4"

            print(f"Lade Clip herunter: {clip_url} als {file_name}")

            # Optionen für yt-dlp
            ydl_opts = {
                "outtmpl": file_name,  # Dateiname mit Template
                "quiet": True,         # Minimale Ausgabe
                # "format": "best",      # Beste verfügbare Qualität
            }

            # yt-dlp Download ausführen
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip_url])
        except Exception as e:
            print(f"Fehler beim Herunterladen von {clip_url}: {e}")


def main():
    """Hauptprogramm."""
    check_dependencies()
    user_name = get_channel_name()
    broadcaster_id = get_broadcaster_id(user_name)
    start_timestamp, end_timestamp = get_time_range()

    print(f"Ermittle Clips für Kanal: {user_name}")
    clips = get_clips(broadcaster_id, start_timestamp, end_timestamp)

    if not clips:
        print("Keine Clips gefunden.")
        return

    print(f"{len(clips)} Clips gefunden. Starte Download...")
    download_clips(clips)
    print("Alle Clips wurden heruntergeladen.")

if __name__ == "__main__":
    main()
