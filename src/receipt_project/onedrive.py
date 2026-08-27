import hashlib
import os
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key


AUTHORITY = "https://login.microsoftonline.com/consumers"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

SCOPES = [
    "offline_access",
    "https://graph.microsoft.com/Files.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]

RECEIPT_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf",
}


def get_access_token() -> str:
    """
    Exchange the stored Microsoft refresh token for a new access token.

    If Microsoft rotates the refresh token, save the newest token back
    into the local .env file when running locally.
    """
    load_dotenv()

    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    refresh_token = os.getenv("MICROSOFT_REFRESH_TOKEN")

    if not client_id:
        raise RuntimeError(
            "MICROSOFT_CLIENT_ID is missing from .env"
        )

    if not refresh_token:
        raise RuntimeError(
            "MICROSOFT_REFRESH_TOKEN is missing from .env"
        )

    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(SCOPES),
        },
        timeout=30,
    )

    response.raise_for_status()
    token_data = response.json()

    access_token = token_data["access_token"]

    new_refresh_token = token_data.get("refresh_token")

    if (
        new_refresh_token
        and new_refresh_token != refresh_token
    ):
        os.environ[
            "MICROSOFT_REFRESH_TOKEN"
        ] = new_refresh_token

        env_path = Path(".env")

        if env_path.exists():
            set_key(
                str(env_path),
                "MICROSOFT_REFRESH_TOKEN",
                new_refresh_token,
            )

    return access_token


def ensure_receipts_folder() -> dict:
    """
    Return the /Receipts OneDrive folder, creating it if necessary.
    """
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    folder_url = (
        f"{GRAPH_BASE_URL}/me/drive/root:/Receipts"
    )

    response = requests.get(
        folder_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        folder = response.json()

        print(
            "OneDrive folder already exists: /Receipts"
        )
        return folder

    if response.status_code != 404:
        response.raise_for_status()

    create_response = requests.post(
        f"{GRAPH_BASE_URL}/me/drive/root/children",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json={
            "name": "Receipts",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        },
        timeout=30,
    )

    create_response.raise_for_status()

    folder = create_response.json()

    print("Created OneDrive folder: /Receipts")
    return folder


def ensure_processed_folder() -> dict:
    """
    Return /Receipts/processed, creating it if necessary.
    """
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    folder_url = (
        f"{GRAPH_BASE_URL}"
        "/me/drive/root:/Receipts/processed"
    )

    response = requests.get(
        folder_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()

    if response.status_code != 404:
        response.raise_for_status()

    create_response = requests.post(
        f"{GRAPH_BASE_URL}"
        "/me/drive/root:/Receipts:/children",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json={
            "name": "processed",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        },
        timeout=30,
    )

    create_response.raise_for_status()

    return create_response.json()


def ensure_review_folder() -> dict:
    """
    Return /Receipts/review, creating it if necessary.
    """
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    folder_url = (
        f"{GRAPH_BASE_URL}"
        "/me/drive/root:/Receipts/review"
    )

    response = requests.get(
        folder_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()

    if response.status_code != 404:
        response.raise_for_status()

    create_response = requests.post(
        f"{GRAPH_BASE_URL}"
        "/me/drive/root:/Receipts:/children",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json={
            "name": "review",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        },
        timeout=30,
    )

    create_response.raise_for_status()

    return create_response.json()


def ensure_extracted_folder() -> dict:
    """
    Return /Receipts/extracted, creating it if necessary.
    """
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    folder_url = (
        f"{GRAPH_BASE_URL}"
        "/me/drive/root:/Receipts/extracted"
    )

    response = requests.get(
        folder_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()

    if response.status_code != 404:
        response.raise_for_status()

    create_response = requests.post(
        f"{GRAPH_BASE_URL}"
        "/me/drive/root:/Receipts:/children",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json={
            "name": "extracted",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        },
        timeout=30,
    )

    create_response.raise_for_status()

    return create_response.json()


def upload_to_receipts(
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> dict:
    """
    Upload a small file to the /Receipts OneDrive landing folder.
    """
    access_token = get_access_token()

    upload_url = (
        f"{GRAPH_BASE_URL}"
        f"/me/drive/root:/Receipts/{filename}:/content"
    )

    response = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
        },
        data=content,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def upload_extraction_json(
    item_id: str,
    original_filename: str,
    json_content: str,
) -> dict:
    """
    Persist structured receipt extraction JSON under
    /Receipts/extracted.

    A stable tag derived from the source OneDrive item ID keeps the
    extraction filename associated with the archived source receipt and
    prevents collisions when different uploads share the same filename.
    """
    access_token = get_access_token()
    extracted_folder = ensure_extracted_folder()

    path = Path(original_filename)

    item_tag = hashlib.sha256(
        item_id.encode("utf-8")
    ).hexdigest()[:12]

    json_filename = (
        f"{path.stem}__{item_tag}.json"
    )

    upload_url = (
        f"{GRAPH_BASE_URL}"
        f"/me/drive/items/{extracted_folder['id']}"
        f":/{json_filename}:/content"
    )

    response = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        data=json_content.encode("utf-8"),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def download_from_receipts(filename: str) -> bytes:
    """
    Download a file from the /Receipts OneDrive landing folder.
    """
    access_token = get_access_token()

    download_url = (
        f"{GRAPH_BASE_URL}"
        f"/me/drive/root:/Receipts/{filename}:/content"
    )

    response = requests.get(
        download_url,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.content


def download_drive_item(item_id: str) -> bytes:
    """
    Download a OneDrive file by its Graph driveItem ID.
    """
    access_token = get_access_token()

    response = requests.get(
        f"{GRAPH_BASE_URL}"
        f"/me/drive/items/{item_id}/content",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.content


def list_receipt_files() -> list[dict]:
    """
    List supported receipt files currently present in /Receipts.

    Handles Microsoft Graph pagination and ignores folders and
    unsupported file types.
    """
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    url = (
        f"{GRAPH_BASE_URL}"
        "/me/drive/root:/Receipts:/children"
    )

    receipt_files = []

    while url:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()
        payload = response.json()

        for item in payload.get("value", []):
            if "file" not in item:
                continue

            name = item.get("name", "")
            suffix = os.path.splitext(name)[1].lower()

            if suffix not in RECEIPT_EXTENSIONS:
                continue

            receipt_files.append(item)

        url = payload.get("@odata.nextLink")

    return receipt_files


def move_drive_item_to_processed(
    item_id: str,
    original_filename: str,
) -> dict:
    """
    Move a OneDrive driveItem into /Receipts/processed.

    The archived filename includes a short stable tag derived from the
    OneDrive item ID so repeated uploads using the same original filename
    do not collide in the processed folder.
    """
    access_token = get_access_token()
    processed_folder = ensure_processed_folder()

    path = Path(original_filename)

    item_tag = hashlib.sha256(
        item_id.encode("utf-8")
    ).hexdigest()[:12]

    archived_name = (
        f"{path.stem}__{item_tag}{path.suffix}"
    )

    response = requests.patch(
        f"{GRAPH_BASE_URL}/me/drive/items/{item_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "parentReference": {
                "id": processed_folder["id"],
            },
            "name": archived_name,
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def move_drive_item_to_review(
    item_id: str,
    original_filename: str,
) -> dict:
    """
    Move a receipt into /Receipts/review.

    A short stable tag based on the OneDrive item ID prevents
    filename collisions while preserving the original filename.
    """
    access_token = get_access_token()
    review_folder = ensure_review_folder()

    path = Path(original_filename)

    item_tag = hashlib.sha256(
        item_id.encode("utf-8")
    ).hexdigest()[:12]

    review_name = (
        f"{path.stem}__{item_tag}{path.suffix}"
    )

    response = requests.patch(
        f"{GRAPH_BASE_URL}/me/drive/items/{item_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "parentReference": {
                "id": review_folder["id"],
            },
            "name": review_name,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def move_receipt_to_processed(filename: str) -> dict:
    """
    Move a receipt from /Receipts into /Receipts/processed.

    Kept for compatibility with existing local scripts.
    """
    access_token = get_access_token()

    processed_folder = ensure_processed_folder()

    item_url = (
        f"{GRAPH_BASE_URL}"
        f"/me/drive/root:/Receipts/{filename}"
    )

    response = requests.get(
        item_url,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=30,
    )

    response.raise_for_status()

    item = response.json()

    move_response = requests.patch(
        f"{GRAPH_BASE_URL}"
        f"/me/drive/items/{item['id']}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "parentReference": {
                "id": processed_folder["id"],
            },
        },
        timeout=30,
    )

    move_response.raise_for_status()

    return move_response.json()