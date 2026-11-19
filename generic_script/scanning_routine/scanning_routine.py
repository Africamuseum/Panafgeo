import paramiko
import os
from datetime import datetime
import subprocess
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

SCRIPT_ROOT = os.getenv("SCRIPT_ROOT")
LOCAL_ROOT = os.getenv("LOCAL_ROOT")
PORT = os.getenv("PORT")
HOSTNAME = os.getenv("HOSTNAME")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
NAS_ROOT = os.getenv("NAS_ROOT")
NAS_PATH = os.getenv("NAS_PATH")
LOCAL_PATH = os.getenv("LOCAL_PATH")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
RECIPIENT_EMAIL_ADDRESSES = os.getenv("RECIPIENT_EMAIL_ADDRESSES")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
COMPUTER_NUMBER = os.getenv("COMPUTER_NUMBER")

def has_any_files(path):
    for root, dirs, files in os.walk(path):
        if files:
            return True
    return False

def get_paths(root, item_name):
    local_path = os.path.join(root, item_name)
    relative_path = local_path.split(f"{LOCAL_PATH}/", 1)[1]
    remote_path = os.path.join(NAS_PATH, relative_path)
    return local_path, remote_path

def needs_transfer(sftp, local_path, remote_path):
    local_stat = os.stat(local_path)
    try:
        remote_stat = sftp.stat(remote_path)
    # File doesn't exist remotely, it needs transfer
    except FileNotFoundError:
        return True

    same_size = local_stat.st_size == remote_stat.st_size
    same_mtime = int(local_stat.st_mtime) == int(remote_stat.st_mtime)

    # The source file is authoritative, if the file exists remotely but has been modified it will be overwriten by the source
    return not (same_size and same_mtime)

def update_directories_modified_date(sftp, path):
    for root, dirs, files in os.walk(path):
        for directory in dirs:
            local_path, remote_path = get_paths(root, directory)
            local_time = os.stat(local_path).st_mtime
            sftp.utime(remote_path, (local_time, local_time))

def send_mail(subject, body):
    app = msal.ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )

    token_response = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    access_token = token_response["access_token"]

    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    email_msg = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": RECIPIENT_EMAIL_ADDRESSES
        }
    }

    response = requests.post(url, headers=headers, json=email_msg)
    if response.status_code != 200 and response.status_code != 202:
        error_data = response.json()
        print("Status code:", response.status_code)
        print("Error code:", error_data.get("error", {}).get("code"))
        print("Error message:", error_data.get("error", {}).get("message"))
        print("Full response:", error_data)
    else:
        print("Email sent successfully!")

if __name__ == '__main__':
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=HOSTNAME, port=PORT, username=USERNAME, password=PASSWORD)

        sftp = ssh_client.open_sftp()

        sftp.chdir(NAS_ROOT)

        if not has_any_files(LOCAL_ROOT):
            raise Exception("There is no files to transfer")
        
        expected_files = []
        uploaded_files = []
        corrupted_files = []
        failed_files = []
        with open(f"{SCRIPT_ROOT}/output.txt", "w") as f:
            for root, dirs, files in os.walk(f"{LOCAL_ROOT}/{LOCAL_PATH}"):
                for directory in dirs:
                    local_path, remote_path = get_paths(root, directory)
                    # The folder will be created if it doesn't exist yet
                    try:
                        sftp.stat(remote_path)
                    except FileNotFoundError:                
                        sftp.mkdir(remote_path)

                for file in files:
                    local_path, remote_path = get_paths(root, file)
                    local_time = os.stat(local_path).st_mtime
                    local_dt = datetime.fromtimestamp(local_time)
                    local_size = os.stat(local_path).st_size
                    
                    if needs_transfer(sftp, local_path, remote_path):
                        expected_files.append(remote_path)
                        try:
                            if local_size == 0:
                                corrupted_files.append(remote_path)
                                f.write(f"Corrupted (0 bytes): {remote_path}\n")
                            else:
                                sftp.put(local_path, remote_path)
                                sftp.utime(remote_path, (local_time, local_time))
                                uploaded_files.append(remote_path)
                                f.write(file + ";" + local_dt.strftime("%Y%m%d%H%M%S") + "\n")
                        except Exception as e:
                            failed_files.append(remote_path)
                            f.write(f"Failed: {remote_path} - {e}\n")
    
            update_directories_modified_date(sftp, f"{LOCAL_ROOT}/{LOCAL_PATH}")
    
            missing = set(expected_files) - set(uploaded_files)

            if missing:
                f.write(f"{len(missing)} files are missing:\n")
                f.write(f" {len(corrupted_files)} corrupted files:\n")
                for corr_file in corrupted_files:
                    f.write(f"  - {corr_file}\n")
                f.write(f" {len(failed_files)} failed files:\n")
                for fail_file in failed_files:
                    f.write(f"  - {fail_file}\n")
            else:
                f.write(f"All {len(expected_files)} files uploaded successfully.")
        
        today = datetime.today().strftime("%Y%m%d")
        sftp.put(f"{SCRIPT_ROOT}/output.txt", f"logs/{COMPUTER_NUMBER}_{today}")
    
        # send_mail("NAS EARTHS010 Completed Scans Transfer task", body)
    
        sftp.close()
        ssh_client.close()

        print("File transfer correctly done")

        subprocess.run(["shutdown", "now"])
    except Exception as e:
        print("An error occured:", e)
