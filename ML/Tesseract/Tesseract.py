import pytesseract
from ML.utils.utils import setup_response
from ML.utils.status import Status

class Tesseract():
    def __init__(self, img, img_path, ops):
        self.img = img
        self.img_path = img_path
        self.ops = ops

    def compute_avg_conf_score(self, conf):
        total_conf = 0
        count = 0
        for c in conf:
            if c != -1:
                total_conf += int(c)
                count += 1
        avg_conf = total_conf / count if count > 0 else 0
        return avg_conf

    def extract_text(self):
        # Batch processing with a single file containing the list of multiple image file paths
        extracted_data = setup_response(self.img_path, "tesseract", self.ops)
        data = pytesseract.image_to_data(self.img, output_type='dict', config='-c preserve_interword_spaces=1,-psm 6')
        # Tesseract good confidence score is 90 or higher on a 0 to 100 scale, where scores above 90 indicate reliable text and values below 70 suggest the output needs manual review or image cleanup.
        avg_conf = self.compute_avg_conf_score(data["conf"])
        level = []
        page_num = []
        block_num = []
        par_num = []
        line_num = []
        word_num = []
        left = []
        top = []
        width = []
        height = []
        conf = []
        text = []
        for i in range(len(data["text"])):
            level.append(data["level"][i])
            page_num.append(data["page_num"][i])
            block_num.append(data["block_num"][i])
            par_num.append(data["par_num"][i])
            line_num.append(data["line_num"][i])
            word_num.append(data["word_num"][i])
            left.append(data["left"][i])
            top.append(data["top"][i])
            width.append(data["width"][i])
            height.append(data["height"][i])
            conf.append(data["conf"][i])
            text.append(data["text"][i])

        extracted_data["score"] = round(avg_conf / 100, 2)
        extracted_data["text"] = " ".join(line.strip() for line in text if line.strip())
        if avg_conf >= 0.7:
            extracted_data["status"] = Status.SUCCEED
        elif avg_conf < 0.7 and avg_conf >= 0.6:
            extracted_data["status"] = Status.NEEDS_REVIEW
        else:
            extracted_data["status"] = Status.FAILED
        return extracted_data
