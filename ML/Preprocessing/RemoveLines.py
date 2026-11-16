import cv2
import numpy as np


class RemoveLines:
    def __init__(self, params):
        self.params = params

    def apply(self, img):
        # Implement the logic to remove lines from the image based on the provided parameters
        #https://stackoverflow.com/questions/51380692/masking-horizontal-and-vertical-lines-with-open-cv/57410471#57410471
        #https://stackoverflow.com/questions/73127943/how-to-crop-an-image-when-detecting-a-straight-line-in-python
        kind = self.params["type"]
        if kind == "vertical_lines":
            return self.remove_vertical_lines(img)
        if kind == "horizontal_lines":
            return self.remove_horizontal_lines(img)
        if kind == "both":
            return self.remove_horizontal_lines(self.remove_vertical_lines(img))
        raise ValueError(f"Unknown type: {kind}")
    
    def remove_horizontal_lines(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        h, w = img.shape[:2]
        ratio = 600 / w
        resized_img = cv2.resize(gray, (0, 0), fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)

        bw = cv2.adaptiveThreshold(cv2.bitwise_not(resized_img), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (bw.shape[1] // 20, 1))

        lines = cv2.dilate(cv2.erode(bw, kernel), kernel)
        lines = cv2.resize(lines, (w, h), interpolation=cv2.INTER_NEAREST)
        lines = cv2.dilate(lines, np.ones((5, 1), np.uint8))
        
        result = img.copy()
        result[lines > 0] = 255
        return result

    def remove_vertical_lines(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(img.shape[0] * 0.3)))
        lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        lines = cv2.dilate(lines, np.ones((1, 5), np.uint8))

        result = img.copy()
        result[lines > 0] = 255
        return result