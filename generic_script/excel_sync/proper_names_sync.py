import os
from dotenv import load_dotenv
import msal
import requests
import io
import pandas as pd

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SITE_ID = os.getenv("SITE_ID")
TENANT_ID = os.getenv("TENANT_ID")
HOSTNAME = os.getenv("HOSTNAME")

excel_list = ["MRAC_Géomines_Manono.xlsm", "AGR_Géomines_Manono.xlsm", "MRAC_CSK.xlsm", "MRAC_DOSSIERS_G.xlsm", "MRAC_Kasai.xlsm"]
proper_names = ["Auteurs", "Entreprises"]

if __name__ == '__main__':
    try:
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
        path_relative_to_root = "MRAC/20_Geologues"
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{path_relative_to_root}:/children"
        response = requests.get(url, headers=headers)
        items = response.json().get("value", [])
        with pd.ExcelWriter("proper_names.xlsx") as writer:
            for name in proper_names:
                values_list = []
                for item in items:
                    print(item["name"])
                    if item["name"] in excel_list:
                        print(item["id"])
                        item_id = item["id"]
                        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
                        response = requests.get(url, headers=headers, stream=True)
                        if response.status_code == 200:
                            bytes_file_obj = io.BytesIO()
                            bytes_file_obj.write(response.content)
                            bytes_file_obj.seek(0)
                            df = pd.read_excel(bytes_file_obj, sheet_name=name)
                            values_list.append(df)
                
                values_df = pd.concat(values_list, ignore_index=True).drop_duplicates("Nom")

                print(len(values_df))
                values_df.to_excel(writer, sheet_name=name, index=False)
    
        print("Synchronization complete")
    except Exception as e:
        print("An exception occurred :", e)