import numpy as np

def fill_id_cols(df):
    df["folder_id"] = df["folder_id"].ffill()
    df["subfolder_id"] = df.groupby(["folder_id"])[["subfolder_id"]].ffill()
    for col in ["subfolder_id"]:
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