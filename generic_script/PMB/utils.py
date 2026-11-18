import numpy as np

def fill_id_cols(df):
    df["N° dossier"] = df["N° dossier"].ffill()
    df["N° sous-dossier"] = df.groupby(["N° dossier"])[["N° sous-dossier"]].ffill()
    for col in ["N° sous-dossier"]:
        df[col] = df[col].fillna(1)
    return df

def relative_folder(df):
    folder_ids_series = df["folder_id"].astype(str).str.zfill(5)
    subfolder_ids_series = df["subfolder_id"].astype(str).str.zfill(2)
    subsubfolder_ids_series = df["subsubfolder_id"].astype(str).str.zfill(2)

    two_level_depth_mask = df["subfolder_id"].notna()
    third_level_depth_mask = df["subsubfolder_id"].notna()

    conditions = [
        two_level_depth_mask & third_level_depth_mask,
        two_level_depth_mask & ~third_level_depth_mask,
    ]
    choices = [
        folder_ids_series + "/" + subfolder_ids_series + "/" + subsubfolder_ids_series,
        folder_ids_series + "/" + subfolder_ids_series,
    ]
    return np.select(conditions, choices, default=folder_ids_series)