import cv2
import numpy as np

class Crop:
    def __init__(self):
        pass

    # Crop image to only have the document : if the document isn’t rectangular, it will be cropped too short
    # Edge case : the shadow of the book pages are detected as the document edges
    # Resources that might help : https://stackoverflow.com/questions/55513477/how-to-find-the-document-edges-in-various-coloured-backgrounds-using-opencv-pyth
    def apply(self, img):
        print("Cropping image...")
        #https://stackoverflow.com/questions/41069831/opencv-python-crop-image-using-numpy-array?rq=1#_=_

        blurred = cv2.GaussianBlur(img, (15, 15), 0)

        # Detect edges - the faint shadow line at the document boundary
        edges = cv2.Canny(blurred, 5, 15)

        # Dilate to close small gaps in the boundary line
        kernel = np.ones((9, 9), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)

        cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # min_line_length = 0.7 * min(img.shape[1], img.shape[0])
        # lines = cv2.HoughLinesP(
        #     edges,
        #     rho=1,
        #     theta=np.pi / 180,
        #     threshold=250,
        #     minLineLength=min_line_length,
        #     maxLineGap=20,
        # )

        # line_img = img.copy()

        # if lines is not None:
        #     for line in lines:
        #         x1, y1, x2, y2 = line
        #     cv2.line(line_img, (x1, y1), (x2, y2), (0, 255, 0), 3)

        largest = max(cnts, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        print(x, y, w, h)

        cropped_img = img[y:y+h, x:x+w]
        return cropped_img