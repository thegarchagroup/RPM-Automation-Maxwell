import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import time
# Load .env from multiple potential paths
_app_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
_root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

if os.path.exists(_app_env):
    load_dotenv(_app_env)
if os.path.exists(_root_env):
    load_dotenv(_root_env)


class DropboxService:
    def __init__(self):
        self.app_key = os.getenv("DROPBOX_APP_KEY")
        self.app_secret = os.getenv("DROPBOX_APP_SECRET")
        self.refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
        self.access_token = None        # fetched via refresh token
        self._token_expiry = 0.0        # unix time when access_token expires
        self.root_namespace_id = os.getenv("DROPBOX_ROOT_NAMESPACE_ID")
    
    def _refresh_access_token(self) -> str:
        if not (self.refresh_token and self.app_key and self.app_secret):
            raise ValueError(
                "Dropbox credentials missing. Set DROPBOX_APP_KEY, DROPBOX_APP_SECRET "
                "and DROPBOX_REFRESH_TOKEN in .env"
            )
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.app_key,
            "client_secret": self.app_secret,
        }).encode("utf-8")
        req = urllib.request.Request("https://api.dropbox.com/oauth2/token", data=data)
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise PermissionError(f"Dropbox token refresh failed: {e.read().decode('utf-8')}")
        self.access_token = res["access_token"]
        # refresh 60s early to be safe
        self._token_expiry = time.time() + res.get("expires_in", 14400) - 60
        return self.access_token


    def _get_active_token(self) -> str:
        if self.access_token and time.time() < self._token_expiry:
            return self.access_token
        return self._refresh_access_token()

    def _path_root_header(self) -> Dict[str, str]:
        """Header needed on every request so paths resolve against the correct
        Dropbox namespace (the team-linked root, not this account's home)."""
        if not self.root_namespace_id:
            return {}
        return {
            "Dropbox-API-Path-Root": json.dumps({
                ".tag": "root",
                "root": self.root_namespace_id,
            })
        }

    def upload_pdf(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        folder_path: str = "/2 - maxwell operations (murray pte ltd)/6 - engineering ops (maxwell)/2 - preventive maintenance/RPM",
        _retry: bool = True,
    ) -> Dict[str, Any]:
        """
        Uploads PDF bytes to Dropbox and returns metadata & a temporary link.
        If no filename is given, uses today's date (YYYY_MM_DD.pdf).
        """
        # Gets a valid access token (refreshes automatically if expired).
        # Raises ValueError / PermissionError if credentials are missing or invalid.
        token = self._get_active_token()

        # Sanitize target path
        clean_folder = folder_path.strip().rstrip("/")
        if not clean_folder.startswith("/"):
            clean_folder = "/" + clean_folder

        if not filename or not filename.strip():
            filename = f"{datetime.now().strftime('%Y_%m_%d')}.pdf"

        clean_filename = filename.strip().replace(" ", "_")
        if not clean_filename.lower().endswith(".pdf"):
            clean_filename += ".pdf"
        target_path = f"{clean_folder}/{clean_filename}"

        upload_url = "https://content.dropboxapi.com/2/files/upload"
        api_args = json.dumps({
            "path": target_path,
            "mode": "overwrite",
            "mute": False,
        })

        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": api_args,
            "Content-Type": "application/octet-stream",
        }
        headers.update(self._path_root_header())

        req = urllib.request.Request(upload_url, data=file_bytes, headers=headers)

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")

            # Token expired mid-flight: force a refresh and retry once
            if e.code == 401 and _retry and "expired_access_token" in error_body:
                self.access_token = None
                return self.upload_pdf(file_bytes, filename, folder_path, _retry=False)

            try:
                err_json = json.loads(error_body)
            except json.JSONDecodeError:
                err_json = {}

            err_tag = err_json.get("error", {}).get(".tag", "") if isinstance(err_json.get("error"), dict) else ""

            if err_tag == "missing_scope":
                req_scope = err_json["error"].get("required_scope", "files.content.write")
                raise PermissionError(
                    f"Dropbox permission scope missing: your app needs '{req_scope}'. "
                    f"Enable 'files.content.write' and 'files.content.read' in the App Console "
                    f"Permissions tab, then generate a new refresh token."
                )
            if e.code == 401:
                raise PermissionError(
                    "Dropbox rejected the access token. Check DROPBOX_APP_KEY, "
                    "DROPBOX_APP_SECRET and DROPBOX_REFRESH_TOKEN in .env."
                )
            raise RuntimeError(f"Dropbox API Error ({e.code}): {error_body}")

        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to connect to Dropbox: {e.reason}")

        path_display = result.get("path_display", target_path)
        share_url = self.get_preview_link(path_display, token)

        return {
            "success": True,
            "message": f"Successfully uploaded {clean_filename} to Dropbox.",
            "path": path_display,
            "size": result.get("size", len(file_bytes)),
            "id": result.get("id"),
            "share_url": share_url,
        }
    
    def get_preview_link(self, dropbox_path: str, token: Optional[str] = None) -> Optional[str]:
        """Attempt to generate a temporary download link."""
        if not token:
            token = self._get_active_token()
        
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            headers.update(self._path_root_header())

            req = urllib.request.Request(
                "https://api.dropboxapi.com/2/files/get_temporary_link",
                data=json.dumps({"path": dropbox_path}).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data.get("link")
        except Exception:
            return None


dropbox_service = DropboxService()