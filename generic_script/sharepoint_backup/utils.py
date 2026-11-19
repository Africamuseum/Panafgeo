import requests
import os
from dotenv import load_dotenv

load_dotenv()

BACKUP_ROOT = os.getenv("BACKUP_ROOT")

def download_file(drive_id, item_id, headers, relative_path):
    global BACKUP_ROOT
    local_path = os.path.join(BACKUP_ROOT, relative_path.lstrip("/"))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
    response = requests.get(url, headers=headers, stream=True)
    with open(local_path, "wb") as f:
        f.write(response.content)

def get_items_in_folders(drive_id, item_id, headers, path):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children"
    response = requests.get(url, headers=headers)
    items = response.json().get("value", [])

    for item in items:
        full_path = f"{path}/{item['name']}"
        if "folder" in item:
            folder_id = item["id"]
            get_items_in_folders(drive_id, folder_id, headers, full_path)
        elif "file" in item:
            file_id = item["id"]
            download_file(drive_id, file_id, headers, full_path)
