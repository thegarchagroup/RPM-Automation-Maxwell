import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

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
        self.access_token = os.getenv("DROPBOX_ACCESS_TOKEN") or self.refresh_token
        # This account's real content (the "AI Garcha" team folder tree) lives
        # under a root namespace different from the account's default/home
        # namespace. Every API call must include the Dropbox-API-Path-Root
        # header with this ID, or paths like "/2 - maxwell operations..."
        # will 404 even though they're visible in the Dropbox UI.
        self.root_namespace_id = os.getenv("DROPBOX_ROOT_NAMESPACE_ID", "15244589731")

    def _get_active_token(self) -> str:
        """
        Returns active token. If refresh token flow is configured and needed, refreshes it.
        """
        # If we have refresh_token and app_key/secret, attempt refresh if needed
        # Otherwise fallback to the provided token
        return self.access_token or self.refresh_token or ""

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
        folder_path: str = "/2 - maxwell operations (murray pte ltd)/6 - engineering ops (maxwell)/2 - preventive maintenance/RPM"
    ) -> Dict[str, Any]:
        """
        Uploads PDF bytes to Dropbox and returns metadata & sharing link.
        If no filename is given, uses today's date (YYYY-MM-DD.pdf).
        """
        token = self._get_active_token()
        if not token:
            raise ValueError("Dropbox credentials missing. Please configure DROPBOX_REFRESH_TOKEN in .env")

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
            "autorename": True,
            "mute": False
        })

        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": api_args,
            "Content-Type": "application/octet-stream"
        }
        headers.update(self._path_root_header())

        # TEMP DEBUG — remove once the upload is confirmed working
        print(f"[dropbox debug] target_path = {target_path}")
        print(f"[dropbox debug] token (last 8 chars) = ...{token[-8:] if token else 'MISSING'}")
        print(f"[dropbox debug] path-root header = {headers.get('Dropbox-API-Path-Root')}")

        req = urllib.request.Request(
            upload_url,
            data=file_bytes,
            headers=headers
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                path_display = result.get("path_display", target_path)
                file_size = result.get("size", len(file_bytes))
                
                # Attempt to generate a temporary download or shared view link
                share_url = self.get_preview_link(path_display, token)

                return {
                    "success": True,
                    "message": f"Successfully uploaded {clean_filename} to Dropbox.",
                    "path": path_display,
                    "size": file_size,
                    "id": result.get("id"),
                    "share_url": share_url
                }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(error_body)
                err_tag = err_json.get("error", {}).get(".tag", "")
                if err_tag == "missing_scope":
                    req_scope = err_json.get("error", {}).get("required_scope", "files.content.write")
                    raise PermissionError(
                        f"Dropbox permission scope missing: Your Dropbox App requires '{req_scope}' permission. "
                        f"Go to Dropbox App Console -> Permissions tab -> Check 'files.content.write' and 'files.content.read', then generate a new token."
                    )
                elif "invalid_access_token" in error_body or "expired_access_token" in error_body:
                    raise PermissionError(
                        "Dropbox token is invalid or expired. Please generate a new token in Dropbox Developer Console."
                    )
                raise RuntimeError(f"Dropbox API Error ({e.code}): {error_body}")
            except (json.JSONDecodeError, PermissionError):
                if isinstance(e, PermissionError):
                    raise
                raise RuntimeError(f"Dropbox upload error ({e.code}): {error_body}")
        except PermissionError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Dropbox: {str(e)}")

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