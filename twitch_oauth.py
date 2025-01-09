import requests

def generate_twitch_oauth_token(client_id, client_secret):
    """
    Generiert ein OAuth-Token für Twitch.

    Args:
        client_id (str): Die Client-ID der Twitch-Anwendung.
        client_secret (str): Das Client-Secret der Twitch-Anwendung.

    Returns:
        dict: Ein Dictionary mit dem Zugriffstoken und anderen Informationen.
    """
    url = "https://id.twitch.tv/oauth2/token"

    # Daten für den Token-Request
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()  # Wirft eine Fehlermeldung bei HTTP-Fehlern

        # Antwort-Daten parsen und zurückgeben
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei der Token-Generierung: {e}")
        return None

# Beispiel-Nutzung
if __name__ == "__main__":
    CLIENT_ID = input("Bitte die Client-ID eingeben: ")
    CLIENT_SECRET = input("Bitte das Client-Secret eingeben: ")

    token_data = generate_twitch_oauth_token(CLIENT_ID, CLIENT_SECRET)

    if token_data:
        print("OAuth-Token erfolgreich generiert:")
        print(token_data)
    else:
        print("Fehler bei der Token-Generierung.")