import concurrent
import cv2
import fitz
import json
import logging
import os
from PIL import Image
from ML.OCR_Pipeline.SftpPool import SftpPool
from ML.utils.utils import read_image, relative_folder
from ML.utils.status import Status

class PdfConverter:
    def __init__(self, nas_root, output_path, hostname, port, username, password):
        self.nas_root = nas_root
        self.output_path = output_path
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

    def ask_db(self, sqlite, folder_id):
        data_df = sqlite.read_folder_pages(["text"], folder_id)
        self.convert(data_df)

    def convert(self, df):
        df = df.assign(relative_folder=relative_folder(df))

        with SftpPool(self.hostname, self.port, self.username, self.password) as pool:
            for relative_path, group in df.groupby("relative_folder"):
                records = json.loads(group.to_json(orient="records"))
                pdf_path = os.path.join(self.output_path, relative_path + ".pdf")
                self.build_pdf(pool, records, pdf_path)

    def build_pdf(self, pool, records, pdf_path):
        doc = fitz.open()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=pool.size) as executor:
                futures = [executor.submit(read_image, pool, obj["img_path"]) for obj in records]

                for obj, future in zip(records, futures):
                    try:
                        img = future.result()
                        self.add_page(doc, img, obj)
                    except Exception as e:
                        logging.warning(f"PDF: skipping {obj['img_path']}: {e}")
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc.save(pdf_path)
        finally:
            doc.close()

    def add_page(self, doc, img, obj):
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        img_w, img_h = pil_img.size
        pil_img_path = self.output_path + obj["img_name"] + ".jpg"
        pil_img.save(pil_img_path)
        try:
            page = doc.new_page(width=img_w, height=img_h)
            page.insert_image(fitz.Rect(0, 0, img_w, img_h), filename=pil_img_path)
            if obj["status"] in [Status.SUCCEED, Status.NEEDS_REVIEW]:
                rect = fitz.Rect(50, 72, img_w - 50, img_h - 72)
                page.insert_textbox(rect, obj["text"], fontsize=33, color=(0, 0, 0))
        finally:
            os.remove(pil_img_path)