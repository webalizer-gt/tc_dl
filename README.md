# tc_dl
Bulk download Twitch-Clips from specific channel and time frame in Python.

## Voraussetzungen
- Python 3.x (In Windows 10/11 über Store installieren!)
- Ein **Twitch-Account**
- Zugang zum Twitch-Developer-Dashboard (nur mit Zwei-Faktor-Auth möglich!)
- Twitch Client-ID und OAuth-Token (siehe unten)
- Die zwei Scripte `tc_dl.py` und `twitch_oauth.py` - lege sie im dem Verzeichnis ab, wo auch die Clips landen sollen

Das Download-Script arbeitet im Verzeichnis, in dem es ausgeführt wird. D.h. dort werden die Clips gespeichert!
  
### **Erforderliche Python-Pakete:**
- `requests`
- `yt-dlp`

Installiere sie in `cmd` mit:
```bash
pip install requests yt-dlp
```

## Anleitung: Clips herunterladen
- Starte das Script `tc_dl.py` über Rechtsklick -> Öffnen mit "Python" oder per `cmd` (`C:\>python tc_dl.py`)
- Gib einen Kanalnamen an oder verwende den Standardnamen durch drücken von `Enter`
- Gib das Datum ein, AB dem Clips geladen werden sollen
- Gib das Datum ein, BIS zu dem Clips geladen werden sollen

# Anleitung: Twitch Client-ID, Client-Secret und OAuth-Token erstellen

Diese Anleitung beschreibt, wie Sie eine Twitch Client-ID, ein Client-Secret sowie ein OAuth-Token erstellen, um die Twitch-API nutzen zu können.

## Voraussetzungen
- Ein **Twitch-Account**

---

## 1. Registrierung einer neuen Twitch-Anwendung

1. Melden Sie sich bei Ihrem [Twitch-Entwickler-Dashboard](https://dev.twitch.tv/console) an.
2. Klicken Sie auf **"Anwendungen"** im linken Menü.
3. Wählen Sie **"Deine Anwendung registrieren"**.
4. Füllen Sie die erforderlichen Felder aus:
   - **Name**: Geben Sie einen Namen für Ihre Anwendung ein (z. B. "tc_dl_twitchname").
   - **OAuth Redirect URLs**: Geben Sie `https://localhost` ein
   - **Kategorie**: Wählen Sie die `Other`.
   - **Client-Typ**: Wählen Sie `Vertraulich`
5. Klicken Sie auf **"Erstellen"**.

Nach der Erstellung wird Ihre Anwendung angezeigt.

---

## 2. Abrufen von Client-ID und des Client-Secrets

1. Klicken Sie im Twitch-Entwickler-Dashboard auf die erstellte Anwendung.
2. Wählen Sie **"Verwalten"** aus.
3. Scrollen Sie nach unten und klicken Sie auf **"Neues Geheimnis"**, um ein neues Client-Secret zu generieren.
4. Kopieren Sie die angezeigte **Client-ID** und das **Client-Secret** und speichern Sie es sicher. Sie werden es für spätere Authentifizierungen benötigen.

> **Hinweis**: Teilen Sie das Client-Secret niemals öffentlich, z. B. in einem Repository. Verwenden Sie `.env`-Dateien oder andere sichere Methoden, um sensible Daten zu speichern.

---

## 3. Generieren eines OAuth-Tokens

Um mit der Twitch-API zu interagieren, benötigen Sie ein OAuth-Token. Folgen Sie den Anweisungen unten, um eines zu generieren.

### 3.1 Token für serverseitige Authentifizierung (Client Credentials Flow)
Dieses Token wird verwendet, wenn kein Benutzerkontext erforderlich ist.

1. Führe das Script `twitch_oauth.py` aus.
2. Füge deine Client-ID und dein Client-Secret ein.
3. Die Antwort enthält das OAuth-Token:
   ```json
   {
     "access_token": "EXAMPLE_TOKEN",
     "expires_in": 3600,
     "token_type": "bearer"
   }
   ```
   - **access_token**: Ihr OAuth-Token
   - **expires_in**: Zeit bis zum Ablauf des Tokens (in Sekunden)
4. Füge Client-ID, OAuth-Token und gewünschten Standard-Kanal oben im Script `tc_dl.py` ein:
   ```python
   # Benutzereingaben (ersetzen mit deinen eigenen Werten)
    CLIENT_ID = "xxxxxxxxxxxxx"  # Deine Twitch Client-ID
    OAUTH_TOKEN = "xxxxxxxxxxx"  # Dein OAuth Token
    DEFAULT_USER_NAME = "sayurilee" # Standard-Kanal
    SPACER = " ¦ "  # Trennzeichen für Dateinamen
    ```

