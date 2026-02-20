
# get_refresh_token.py

import os
from dotenv import load_dotenv
import secrets
import urllib.parse
from flask import Flask, request
import requests

"""
One-time helper to obtain a Google OAuth refresh token for Calendar API.

How it works:
- Starts a local server at http://localhost:8787
- Opens an authorization URL you paste into a browser
- Google redirects back with a code
- Script exchanges code for tokens and prints the refresh_token

Required env vars:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET

Optional:
- GOOGLE_OAUTH_PORT (default 8787)

Scopes:
- https://www.googleapis.com/auth/calendar.events (create/edit events)
"""

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
PORT = int(os.getenv("GOOGLE_OAUTH_PORT", "8787"))

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise SystemExit("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars first.")

REDIRECT_URI = f"http://localhost:{PORT}/oauth2callback"
SCOPE = "https://www.googleapis.com/auth/calendar.events"

app = Flask(__name__)
STATE = secrets.token_urlsafe(16)

@app.route("/")
def index():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",      # required to receive refresh_token
        "prompt": "consent",           # force refresh_token issuance (important)
        "state": STATE,
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return (
        "<h2>Google OAuth Refresh Token Helper</h2>"
        "<p>1) Click the link below and complete consent.</p>"
        f'<p><a href="{url}">Authorize with Google</a></p>'
        "<p>2) After approving, you’ll be redirected back and the refresh token will be shown.</p>"
    )

@app.route("/oauth2callback")
def oauth2callback():
    if request.args.get("state") != STATE:
        return "State mismatch. Abort.", 400

    code = request.args.get("code")
    if not code:
        return f"Missing code. Params: {dict(request.args)}", 400

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )

    token_json = token_resp.json()
    if token_resp.status_code != 200:
        return f"Token exchange failed: {token_json}", 500

    refresh_token = token_json.get("refresh_token")
    access_token = token_json.get("access_token")

    if not refresh_token:
        # Common reasons:
        # - you didn't set prompt=consent and access_type=offline
        # - you already authorized this client+user and Google didn't re-issue a refresh token
        return (
            "<h3>No refresh_token returned.</h3>"
            "<p>This usually means Google did not re-issue it.</p>"
            "<ul>"
            "<li>Make sure prompt=consent and access_type=offline are set (this script does).</li>"
            "<li>Go to https://myaccount.google.com/permissions and remove the app, then try again.</li>"
            "</ul>"
            f"<pre>{token_json}</pre>",
            200,
        )

    # Print to terminal too (handy)
    print("\n=== SUCCESS ===")
    print("REFRESH_TOKEN:\n", refresh_token)
    print("\nACCESS_TOKEN (short-lived):\n", access_token)

    return (
        "<h2>Success ✅</h2>"
        "<p>Copy this refresh token and store it as a Cloudflare Worker secret:</p>"
        f"<pre>{refresh_token}</pre>"
        "<p>You can now close this tab.</p>"
    )

if __name__ == "__main__":
    print(f"Open http://localhost:{PORT} in your browser")
    app.run(host="0.0.0.0", port=PORT, debug=False)