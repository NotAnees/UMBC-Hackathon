# Phishing Detector — Chrome Extension

Reads your Gmail via the Gmail API and scores each message with the blue-team
detector's `/analyze` endpoint. Two surfaces:

- **Popup** (toolbar icon): load your inbox and analyze messages on demand — reliable.
- **Inline banner**: a verdict banner injected above the open email in Gmail — best-effort.

It only ever **reads** Gmail (`gmail.readonly`) and only talks to `gmail.googleapis.com`
and your local detector at `http://localhost:8000`.

## Prerequisites
- The stack is running (`docker compose up`), so `http://localhost:8000/analyze` is up.
- You've enabled the **Gmail API** and have an OAuth consent screen with your account as a
  **test user** (done during the seeder setup).

## One-time setup (the OAuth "chicken-and-egg")
A Chrome-Extension OAuth client is tied to the extension's ID, which you only get after
loading it. So:

1. **Load the extension unpacked**
   - Go to `chrome://extensions`, enable **Developer mode**, click **Load unpacked**,
     and select this `extension/` folder.
   - Copy the **extension ID** shown on its card.
   - (Keep this folder where it is — an unpacked extension's ID is tied to its path.)
2. **Add the read scope** to your OAuth consent screen: `https://www.googleapis.com/auth/gmail.readonly`.
3. **Create the OAuth client**: Google Cloud Console → APIs & Services → Credentials →
   Create Credentials → OAuth client ID → **Application type: Chrome Extension** → paste
   the extension ID from step 1. Copy the generated **client ID**.
4. **Paste it into `manifest.json`** — replace `PASTE_YOUR_CHROME_EXTENSION_CLIENT_ID_HERE...`
   with your client ID.
5. Back on `chrome://extensions`, click **Reload** on the extension.

## Use it
1. Click the extension's toolbar icon → **Load inbox** (first time, approve the Google
   sign-in). Click **Analyze** on any message, or **Analyze all**.
2. For the inline banner: after signing in via the popup once, open any email in Gmail —
   a colored verdict banner appears above it.

## Testing with synthetic phishing
Use the seeder to drop test attacks into your own inbox, then analyze them here:
```
python redteam/gmail_insert.py --count 5
```

## Notes
- The backend URL is `http://localhost:8000` (set at the top of `background.js`). Change it
  if you host the detector elsewhere.
- CORS is already open on the detector API, so the extension can call it directly.
- The client ID for a Chrome-Extension OAuth client is not a secret (there's no client
  secret), so it's safe to keep in `manifest.json`.
