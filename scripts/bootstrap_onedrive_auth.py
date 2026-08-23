import base64
import hashlib
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv, set_key


AUTHORITY = "https://login.microsoftonline.com/consumers"
AUTHORIZE_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"

SCOPES = [
    "offline_access",
    "https://graph.microsoft.com/Files.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]

GRAPH_DRIVE_URL = "https://graph.microsoft.com/v1.0/me/drive"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)

        self.__class__.result = {
            "code": query.get("code", [None])[0],
            "state": query.get("state", [None])[0],
            "error": query.get("error", [None])[0],
            "error_description": query.get(
                "error_description", [None]
            )[0],
        }

        message = (
            "Microsoft authentication received. "
            "You can close this browser tab and return to the terminal."
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def base64url_without_padding(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def main():
    load_dotenv()

    client_id = os.getenv("MICROSOFT_CLIENT_ID")

    if not client_id:
        raise RuntimeError(
            "MICROSOFT_CLIENT_ID is missing from .env"
        )

    # PKCE
    code_verifier = base64url_without_padding(
        secrets.token_bytes(64)
    )

    code_challenge = base64url_without_padding(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    )

    state = secrets.token_urlsafe(32)

    # Let the OS choose a free local port.
    server = HTTPServer(("localhost", 0), OAuthCallbackHandler)
    port = server.server_address[1]

    redirect_uri = f"http://localhost:{port}"

    authorization_params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    authorization_url = (
        f"{AUTHORIZE_URL}?{urlencode(authorization_params)}"
    )

    print("Opening Microsoft sign-in in your browser...")
    print(f"Local callback: {redirect_uri}")

    opened = webbrowser.open(authorization_url)

    if not opened:
        print("\nOpen this URL manually:\n")
        print(authorization_url)

    server.timeout = 300
    server.handle_request()
    server.server_close()

    result = OAuthCallbackHandler.result

    if result.get("error"):
        raise RuntimeError(
            f"Microsoft authorization failed: "
            f"{result['error']} - "
            f"{result.get('error_description')}"
        )

    authorization_code = result.get("code")

    if not authorization_code:
        raise RuntimeError(
            "No authorization code was returned."
        )

    if result.get("state") != state:
        raise RuntimeError("OAuth state validation failed.")

    token_response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "scope": " ".join(SCOPES),
        },
        timeout=30,
    )

    token_response.raise_for_status()
    token_data = token_response.json()

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")

    if refresh_token:
        # Store locally only. .env is already ignored by Git.
        set_key(
            ".env",
            "MICROSOFT_REFRESH_TOKEN",
            refresh_token,
        )

    drive_response = requests.get(
        GRAPH_DRIVE_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=30,
    )

    drive_response.raise_for_status()
    drive = drive_response.json()

    print()
    print("Microsoft OAuth login: SUCCESS")
    print(
        "Refresh token received:",
        "YES" if refresh_token else "NO",
    )
    print("Microsoft Graph /me/drive: SUCCESS")
    print(f"Drive type: {drive.get('driveType')}")
    print(f"Drive ID returned: {'YES' if drive.get('id') else 'NO'}")


if __name__ == "__main__":
    main()
