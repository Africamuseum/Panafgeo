import json
import os
from ML.utils.utils import relative_folder

class JsonConverter:
    def __init__(self, output_path):
        self.output_path = output_path

    def ask_db(self, sqlite, folder_id):
        data_df = sqlite.read_folder_pages(["*"], folder_id)
        self.convert(data_df)

    def convert(self, df):
        df = df.assign(relative_folder=relative_folder(df))

        for relative_path, group in df.groupby("relative_folder"):
            records = json.loads(group.drop(columns="relative_folder").to_json(orient="records"))
            json_path = os.path.join(self.output_path, relative_path + ".json")
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=4, ensure_ascii=False)