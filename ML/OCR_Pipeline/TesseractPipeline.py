from ML.Tesseract.Tesseract import Tesseract
from ML.Preprocessing.Preprocessing import Preprocessing

class TesseractPipeline:
    def __init__(self, ops):
        self.ops = ops
    def process(self, img, img_path):
        try:
            preprocessed_img = Preprocessing(self.ops).process(img)
        except Exception as e:
            raise RuntimeError(f"Preprocessing failed for {img_path}: {e}") from e
        try:
            return Tesseract(preprocessed_img, img_path, self.ops).extract_text()
        except Exception as e:
            raise RuntimeError(f"Tesseract failed for {img_path}: {e}") from e
