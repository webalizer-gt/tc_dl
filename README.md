# tc_dl
Bulk download Twitch clips from a specific channel and time frame written in Python.

## Prerequisites
- Python 3.x (Install via Store on Windows 10/11!)
- A **Twitch account**
- Access to the Twitch Developer Dashboard (only possible with two-factor authentication!)
- Twitch Client-ID and OAuth token (see below)
- The two scripts `tc_dl.py` and `twitch_oauth.py` - place them in the directory where the clips should be saved

The download script works in the directory where it is executed. This means that the clips will be saved there!
  
### **Required Python packages:**
- `requests`
- `yt-dlp`

Install them in `cmd` with:
```bash
pip install requests yt-dlp
```

## Configure the script
1. Run the script `tc_dl.py` with the option -c. You can do this by right-clicking the file and selecting "Open with Python" or by using the command line:
    ```bash
    C:\Directory\>python tc_dl.py -c
    ```
2. Enter a default channel name you want to downloads clips from.
3. Enter a download folder eg. `C:\Username\TwitchClips`
4. Enter a spacer combination that separates information in you filenames
5. Enter Twitch Client-ID -> see instructions below how to get this
6. Enter Twitch Secret -> see instructions below how to get this

## Instructions: Download clips
1. Run the script `tc_dl.py`. You can do this by right-clicking the file and selecting "Open with Python" or by using the command line:
    ```bash
    C:\Directory\>python tc_dl.py
    ```
2. Enter a channel name or use the default name by pressing `Enter`
3. Enter the date FROM which clips should be loaded
4. Enter the date UNTIL which clips should be loaded


# Instructions: Create Twitch Client-ID, Client-Secret, and OAuth-Token

This guide describes how to create a Twitch Client-ID, a Client-Secret, and an OAuth-Token to use the Twitch API.

## Prerequisites
- A **Twitch account**

---

## 1. Register a new Twitch application

1. Log in to your [Twitch Developer Dashboard](https://dev.twitch.tv/console).
2. Click on **"Applications"** on the left menu.
3. Select **"Register Your Application"**.
4. Fill in the required fields:
   - **Name**: Enter a name for your application (e.g., "tc_dl_twitchname").
   - **OAuth Redirect URLs**: Enter `https://localhost`
   - **Category**: Select `Other`.
   - **Client Type**: Select `Confidential`
5. Click on **"Create"**.

After creation, your application will be displayed.

---

## 2. Retrieve Client-ID and Client-Secret

1. Click on the created application on the Twitch Developer Dashboard.
2. Select **"Manage"**.
3. Scroll down and click on **"New Secret"** to generate a new Client-Secret.
4. Copy the displayed **Client-ID** and **Client-Secret** and save them securely. You will need them for future authentications.

> **Note**: Never share the Client-Secret publicly, e.g., in a repository. Use `.env` files or other secure methods to store sensitive data.

---

## 3. Generate an OAuth-Token

The OAuth token get generated and saved by the script. No need to worry about.
