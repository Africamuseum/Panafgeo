import cv2
import numpy as np


class SegmentateLines:
    def __init__(self):
        pass

    def apply(self, img):
        # Implement the logic to segment lines from the image based on the provided parameters
        #https://stackoverflow.com/questions/71754254/text-line-segmentation-using-opencv-python
        h, w = img.shape[:2]
        rescale_ratio = 330 / w
        resized_img = cv2.resize(img, (0, 0), fx=rescale_ratio, fy=rescale_ratio, interpolation=cv2.INTER_AREA)
        rescale_ratio = 1 / rescale_ratio
        
        ret, thresh = cv2.threshold(resized_img,0,255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # dilate threshold
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        horizontal = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # find contours and bounding boxes
        bboxes = []
        segments = []
        horizontal_contours, hierarchy = cv2.findContours(horizontal, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        for cnt in horizontal_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            x = int(np.rint(x * rescale_ratio))
            y = int(np.rint(y * rescale_ratio))
            w = int(np.rint(w * rescale_ratio))
            h = int(np.rint(h * rescale_ratio))
            bboxes.append((x, y, w, h))
        bboxes = self.is_nested_bboxes(bboxes)
        bboxes_img = img.copy()
        for (x, y, w, h) in bboxes:
            cv2.rectangle(bboxes_img, (x, y), (x + w, y + h), (0, 0, 255), 1)
        for j in range(len(bboxes)):
            (x, y, w, h) = bboxes[j]
            y_start = y - 10 if y >= 10 else 0
            y_end = y + h + 10 if y <= img.shape[0] - h - 10 else img.shape[0]
            x_start = x - 10 if x >= 10 else 0
            x_end = x + w + 10 if x <= img.shape[1] - w - 10 else img.shape[1]
            segment = img[y_start:y_end, x_start:x_end]
            segments.append(segment)
        return segments

    def is_nested_bboxes(self, bboxes):
        to_remove = set()
        n = len(bboxes)
        for i in range(n):
            x1 = bboxes[i][0]
            y1 = bboxes[i][1]
            x2 = bboxes[i][0] + bboxes[i][2]
            y2 = bboxes[i][1] + bboxes[i][3]
            for j in range(n):
                if i == j or j in to_remove:
                    continue
                x1p = bboxes[j][0]
                y1p = bboxes[j][1]
                x2p = bboxes[j][0] + bboxes[j][2]
                y2p = bboxes[j][1] + bboxes[j][3]
                if x1 < x1p and y1 < y1p and x2 > x2p and y2 > y2p:
                    to_remove.add(j)

        return [b for idx, b in enumerate(bboxes) if idx not in to_remove]