import asyncio
import concurrent
import cv2
import datetime
from dotenv import load_dotenv
import logging
import os
import pandas as pd
from ML.OCR_Pipeline.Sqlite import Sqlite
from ML.Preprocessing.Preprocessing import Preprocessing
from ML.OCR_Pipeline.Qwen import Qwen
from ML.OCR_Pipeline.QwenPipeline import QwenPipeline
from ML.OCR_Pipeline.TesseractPipeline import TesseractPipeline
from ML.OCR_Pipeline.SftpConnection import SftpConnection
from ML.OCR_Pipeline.SftpPool import SftpPool
from ML.OCR_Pipeline.PdfConverter import PdfConverter
from ML.utils.utils import load_ops, read_image, get_file_b64, decompose_folder_structure
from ML.OCR_Pipeline.JsonConverter import JsonConverter
from ML.OCR_Pipeline.Accuracy import Accuracy
from ML.utils.status import Status

load_dotenv()

OUTPUT_PATH = os.getenv("OUTPUT_PATH")
NAS_ROOT=os.getenv("NAS_ROOT")
PORT=os.getenv("PORT")
HOSTNAME=os.getenv("HOSTNAME")
USERNAME=os.getenv("USERNAME")
PASSWORD=os.getenv("PASSWORD")
URL = os.getenv("URL")
MODEL = os.getenv("MODEL")
PROMPT = os.getenv("PROMPT")

def tesseract_process(pipeline, extracted_data_list):
    """
    Reading from the NAS is really slow with a single thread, so a pool of eight SSH and SFTP connections is created and the 
    images are read concurrently by eight threads. The executor only reads images that failed during Qwen processing.
    After reading operation, the image are preprocessed one by one and sent to Tesseract. The Tesseract result replaces the original record 
    only if its status is "succeed" or "needs_review", otherwise the original record is kept.

    Args:
        extracted_data_list (list of dictionaries): the text and other related data extracted from each pages.
    
    Returns:
        list[dict]: The same list, with records updated in place where Tesseract succeeded.
    """
    print("Total pages to process: ", len(extracted_data_list))


    with SftpPool(HOSTNAME, PORT, USERNAME, PASSWORD) as pool:
        with concurrent.futures.ThreadPoolExecutor(max_workers=pool.size) as executor:
            futures_to_idx = {executor.submit(read_image, pool, obj["img_path"]): i for i, obj in enumerate(extracted_data_list) if obj["status"] not in [Status.SUCCEED]}
            # futures_to_idx = {executor.submit(read_image, pool, obj["img_path"]): i for i, obj in enumerate(extracted_data_list)}
            for future in concurrent.futures.as_completed(futures_to_idx):
                i = futures_to_idx[future]
                obj = extracted_data_list[i]
                if i % 50 == 0:
                    print(i)
                try:
                    img = future.result()
                    extracted_data = pipeline.process(img, obj["img_path"])
                except (FileNotFoundError, ValueError, RuntimeError) as e:
                    print(f"{obj['img_path']}: {e}")
                    obj["error"] = str(e)
                    obj["status"] = "err"
                    continue
                # if extracted_data["status"] in [Status.SUCCEED, Status.NEEDS_REVIEW]:
                #     extracted_data_list[i] = extracted_data
                if obj["score"] < extracted_data["score"]:
                    extracted_data_list[i] = extracted_data
    return extracted_data_list

def save_records(db, extracted_data_list):
    """
    Save the extracted data from images in the database.

    Args:
        db (object): Database instance used to store the records, one per image.
        extracted_data_list (list[dict]): Extracted data for each image.
    """

    cols_to_keep = ["folder_id", "subfolder_id", "subsubfolder_id", "file_id", "img_name", "extension", "img_path", "engine", "params", "text", "error", "score", "status"]

    extracted_data_df = pd.DataFrame(extracted_data_list)

    extracted_data_df = decompose_folder_structure(extracted_data_df)

    if "error" not in extracted_data_df.columns:
        extracted_data_df["error"] = None

    extracted_data_df = extracted_data_df[cols_to_keep]

    db.create(extracted_data_df)

    return extracted_data_df

folder_ids = ["RJCB-1951"]


if __name__ == '__main__':
    try:
        start = datetime.datetime.now()

        qwen_ops = load_ops("ML/OCR_Pipeline/qwen_ops.json")
        tesseract_ops = load_ops("ML/OCR_Pipeline/tesseract_ops.json")
        qwen = Qwen(URL, MODEL, PROMPT, qwen_ops)
        qwen_pipeline = QwenPipeline(qwen, 120, 16)
        tesseract_pipeline = TesseractPipeline(tesseract_ops)
        accuracy = Accuracy(MODEL.split("/")[-1])
        logging.basicConfig(
            filename="ocr_pipeline.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        for folder_id in folder_ids:
            try:
                print("Folder in processing: ", folder_id)
                folder_path = os.path.join(NAS_ROOT, folder_id)
                print(folder_path)

                with SftpConnection(HOSTNAME, PORT, USERNAME, PASSWORD) as connection:
                    img_paths = connection.list_files(folder_path)
                img_paths_list = [path for path in img_paths if path.endswith(("jpg", ".jp2", ".tif"))]
                img_paths_list.sort()

                print("Encoding in base 64...")
                with SftpPool(HOSTNAME, PORT, USERNAME, PASSWORD) as pool:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=pool.size) as executor:
                        futures = {executor.submit(read_image, pool, img_path): img_path for img_path in img_paths_list}

                        url64_dict = {}
                        for future in concurrent.futures.as_completed(futures):
                            img_path = futures[future]
                            try:
                                img = future.result()
                                preprocessed_img = Preprocessing(qwen_ops).process(img)
                                url64_dict[img_path] = get_file_b64(preprocessed_img)
                            except Exception as e:
                                logging.warning(f"Skipping {img_path}: {e}")
                                continue
                        validated_paths = [img_path for img_path in img_paths_list if img_path in url64_dict]
                        url64_list = [url64_dict[img_path] for img_path in validated_paths]

                print("Processing with Qwen...")
                print("Total pages to process: ", len(validated_paths))
                extracted_data_list = asyncio.run(qwen_pipeline.run(validated_paths, url64_list))

                print("Processing with Tesseract...")
                extracted_data_list = tesseract_process(tesseract_pipeline, extracted_data_list)

                #print("Inserting into SQLite db...")
                #with Sqlite("panafgeo_ocr.db") as db:
                #    extracted_data_df = save_records(db, extracted_data_list)
                cols_to_keep = ["folder_id", "subfolder_id", "subsubfolder_id", "file_id", "img_name", "extension", "img_path", "engine", "params", "text", "error", "score", "status"]
                extracted_data_df = pd.DataFrame(extracted_data_list)
                extracted_data_df = decompose_folder_structure(extracted_data_df)
                if "error" not in extracted_data_df.columns:
                    extracted_data_df["error"] = None
                extracted_data_df = extracted_data_df[cols_to_keep]

                if "error" not in extracted_data_df.columns:
                    extracted_data_df["error"] = None

                print("Converting to JSON...")
                JsonConverter(OUTPUT_PATH).convert(extracted_data_df)

                print("Converting to PDF...")
                PdfConverter(NAS_ROOT, OUTPUT_PATH, HOSTNAME, PORT, USERNAME, PASSWORD).convert(extracted_data_df)

                print("Computing accuracy score...")
                try:
                    accuracy.add_folder(folder_id, extracted_data_df)
                except Exception:
                    logging.exception(f"Folder {folder_id}: accuracy computation failed")

                logging.info(f"Folder {folder_id} done: {len(validated_paths)}/{len(img_paths_list)} pages sent to extraction")
            except Exception:
                logging.exception(f"Folder {folder_id} failed")
                continue

        print("Computing total accuracy score...")
        try:
            accuracy.summary()
        except Exception:
            logging.exception(f"Summary computation failed")

        print("Runtime for batch processing: ", str(datetime.datetime.now() - start))
    except Exception as e:
        raise("Unexpected error: ", e)
