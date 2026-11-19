import argparse
import msal
import requests
from utils import get_items_in_folders
from time import strftime, localtime
import os
from dotenv import load_dotenv
import subprocess

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SITE_URL = os.getenv("SITE_URL")
SITE_ID = os.getenv("SITE_ID")
TENANT_ID = os.getenv("TENANT_ID")
BACKUP_ROOT = os.getenv("BACKUP_ROOT")
HOSTNAME = os.getenv("HOSTNAME")

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--rotation", metavar="path", required=True)
        args = parser.parse_args()

        rotation_folder = args.rotation
        backup_folder = strftime("%Y%m%d%H%M%S", localtime())
        os.makedirs(f"{BACKUP_ROOT}/{rotation_folder}/{backup_folder}", exist_ok=True)

        app = msal.ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )

        token_response = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        access_token = token_response["access_token"]

        url = f"https://graph.microsoft.com/v1.0/sites/{HOSTNAME}:/sites/{SITE_ID}"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{HOSTNAME}:/sites/{SITE_ID}",
            headers=headers
        )
        site_id = response.json()["id"]

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        response = requests.get(url, headers=headers)
        drives = response.json()["value"]
        drive_id = drives[0]["id"]

        get_items_in_folders(drive_id, "root", headers, f"{rotation_folder}/{backup_folder}")
        
        parent_folder = os.path.join(BACKUP_ROOT, rotation_folder)
        zip_path = f"{backup_folder}.zip"
        result = subprocess.run(["zip", "-rm", zip_path, backup_folder], capture_output=True, text=True, cwd=parent_folder)
        print("Backup complete")
    except Exception as e:
        print("An exception occurred :", e)



