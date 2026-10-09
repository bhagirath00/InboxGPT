"""Google OAuth 2.0 flow and token management for Gmail API."""

from pathlib import Path
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from inboxgpt.config import logger
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from inboxgpt.config import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_credentials(interactive: bool = False) -> Optional[Credentials]:
    """Retrieve valid user credentials from disk, refreshing if expired.

    If credentials are missing or invalid and interactive is True, triggers the OAuth flow.
    """
    import json
    creds = None
    token_path = config.token_file

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            # Fallback: load directly from token JSON dictionary
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                creds = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=token_data.get("scopes") or SCOPES,
                )
            except Exception:
                creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save the refreshed token
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            logger.info("Successfully refreshed Google OAuth token.")
        except RefreshError as e:
            logger.warning("Google OAuth token expired or was revoked: %s. Purging stale token.", e)
            try:
                token_path.unlink(missing_ok=True)
            except Exception:
                pass
            creds = None
        except Exception as e:
            logger.warning("Unexpected error refreshing Google OAuth token: %s", e)
            creds = None

    if not creds or not creds.valid:
        if interactive:
            creds = run_oauth_flow()
        else:
            return None

    return creds


def run_oauth_flow(
    credentials_path: Optional[Path] = None,
    port: int = 0,
    select_account: bool = False,
) -> Credentials:
    """Execute the browser-based OAuth 2.0 consent flow and store the token."""
    client_id = config.get_google_client_id()
    client_secret = config.get_google_client_secret()

    if client_id and client_secret:
        # Check both web and installed client formats for Google OAuth
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    "http://localhost:8080/",
                    "http://localhost:8080",
                    "http://127.0.0.1:8080/",
                    "http://localhost:3000/api/auth/callback",
                ],
            }
        }
        try:
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        except Exception:
            client_config["installed"] = client_config.pop("web")
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    else:
        creds_file = credentials_path or config.get_credentials_path()

        if not creds_file.exists():
            raise FileNotFoundError(
                f"Google client secrets not found!\n"
                f"Provide GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env, "
                f"or save your credentials JSON to: {config.credentials_file}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)

    # Use fixed port 8080 by default for authorized redirect matching, fallback to dynamic
    target_port = port or 8080
    success_text = "Authentication Successful! InboxGPT is now connected to your Gmail account. You may close this tab and return to your terminal."

    prompt_msg = (
        "\n[bold green]Opening your browser for Google Sign-In...[/bold green]\n"
        "[dim]If your browser does not pop up automatically, click or copy this link:[/dim]\n"
        "[bold underline cyan]{url}[/bold underline cyan]\n"
    )

    # Execute single, atomic OAuth local server flow on authorized port 8080
    creds = flow.run_local_server(
        port=target_port,
        open_browser=True,
        authorization_prompt_message=prompt_msg,
        success_message=success_text,
        access_type="offline",
        prompt="consent select_account" if select_account else "consent",
    )

    # Persist the new credentials to ~/.inboxgpt/token.json
    config.token_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config.token_file, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    # Try to detect and cache authenticated email
    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        if profile and profile.get("emailAddress"):
            config.update_settings({"last_authenticated_email": profile["emailAddress"]})
    except Exception:
        pass

    return creds


def get_auth_status() -> Dict[str, Any]:
    """Inspect current authentication state for Gmail and Gemini."""
    has_creds_file = config.has_google_credentials()
    has_token = config.has_google_token()
    creds = get_credentials(interactive=False) if has_token else None
    token_valid = bool(creds and (creds.valid or creds.refresh_token))

    gemini_key = config.get_gemini_api_key()
    cached_email = config.get_settings().get("last_authenticated_email")

    return {
        "google_credentials_file_found": has_creds_file,
        "credentials_path": str(config.get_credentials_path()),
        "google_token_found": has_token,
        "google_token_valid": token_valid,
        "gemini_api_key_configured": bool(gemini_key),
        "is_ready_live": token_valid and bool(gemini_key),
        "email": cached_email,
    }
