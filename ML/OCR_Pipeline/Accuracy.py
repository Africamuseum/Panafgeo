import pandas as pd
from ML.utils.status import Status


class Accuracy:
    def __init__(self, model):
        self.model = model
        self.folders = {}

    def ask_db(self, sqlite, folder_id):
        df = sqlite.read_folder_pages(["status", "score", "engine", "error"], folder_id)
        self.add_folder(folder_id, df)

    def add_folder(self, folder_id, df):
        total = len(df)
        if total == 0:
            print(f"Folder {folder_id}: no page, accuracy not computed.")
            return

        scores = pd.to_numeric(df["score"], errors="coerce").where(df["error"].isna(), 0).fillna(0)

        qwen_mask = df["engine"] == self.model
        tesseract_mask = df["engine"] == "tesseract"

        qwen_len = int(qwen_mask.sum())
        tesseract_len = int(tesseract_mask.sum())
        qwen_score_sum = float(scores[qwen_mask].sum())
        tesseract_score_sum = float(scores[tesseract_mask].sum())

        succeed_count = int((df["status"] == Status.SUCCEED).sum())
        needs_review_count = int((df["status"] == Status.NEEDS_REVIEW).sum())
        failed_count = int((~df["status"].isin([Status.SUCCEED, Status.NEEDS_REVIEW])).sum())

        self.folders[folder_id] = {
            "succeed_count": succeed_count,
            "needs_review_count": needs_review_count,
            "failed_count": failed_count,
            "total": total,
            "qwen_len": qwen_len,
            "qwen_score_sum": qwen_score_sum,
            "tesseract_len": tesseract_len,
            "tesseract_score_sum": tesseract_score_sum,
        }

        print(f"--- Folder {folder_id} ---")
        self.print_stats(self.folders[folder_id])

    def summary(self):
        if not self.folders:
            print("No folder was processed, no summary available.")
            return

        totals = pd.DataFrame(self.folders).T.sum()
        print(f"--- Summary of {len(self.folders)} folder(s) ---")
        self.print_stats(totals)

    def print_stats(self, stats):
        success_rate = stats["succeed_count"] / stats["total"]
        qwen_avg = stats["qwen_score_sum"] / stats["qwen_len"] if stats["qwen_len"] else 0
        tesseract_avg = stats["tesseract_score_sum"] / stats["tesseract_len"] if stats["tesseract_len"] else 0

        print(f'Pages flagged as "succeed": {stats["succeed_count"]}')
        print(f'Pages flagged as "needs_review": {stats["needs_review_count"]}')
        print(f'Pages flagged as "failed or err": {stats["failed_count"]}')
        print(f"Success rate: {success_rate:.3f}")
        print(f'Pages processed by Qwen: {stats["qwen_len"]}')
        print(f'Pages processed by Tesseract: {stats["tesseract_len"]}')
        print(f"Average score for Qwen (log probability): {qwen_avg:.3f}, beyond 0.75 is good")
        print(f"Average score for Tesseract (confidence): {tesseract_avg:.1f}, beyond 0.8 is good")