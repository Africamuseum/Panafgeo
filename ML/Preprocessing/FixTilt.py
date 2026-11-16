import cv2
import numpy as np
import math

class FixTilt:
    def __init__(self):
        pass

    def apply(self, img):
        # Implement deskewing logic here
        avg_degree = self.get_degree(img)
        fixed_img = self.move_of_degree(img, avg_degree)
        return fixed_img

    def get_degree(self, img):
        # Implement logic to calculate the average angle of skew in the image
        blur = cv2.GaussianBlur(img, (5, 5), 0)
        ret, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        edges = cv2.Canny(thresh, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 250, min_theta=np.deg2rad(70), max_theta=np.deg2rad(110))
        sum_rad = 0
        nb_lines = 0
        if lines is not None:
            for line in lines:
                rho, theta = line[0]
                if theta!=0:
                    sum_rad += theta
                    nb_lines += 1
                # a = np.cos(theta)
                # b = np.sin(theta)
                # x0 = a * rho
                # y0 = b * rho
                # x1 = int(x0 + 1000 * (-b))
                # y1 = int(y0 + 1000 * (a))
                # x2 = int(x0 - 1000 * (-b))
                # y2 = int(y0 - 1000 * (a))
                # cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            # cv2.imwrite('houghlines.tif', img)
            if nb_lines != 0:
                avg_rad = sum_rad / nb_lines
                avg_deg = math.degrees(avg_rad) - 90
                # print(avg_deg)
                return avg_deg
            else:
                return 0
    
    def move_of_degree(self, img, avg_deg):
        h, w = img.shape[0], img.shape[1]
        M = cv2.getRotationMatrix2D((0, 0), avg_deg, 1)
        deskewed_img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode = cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        return deskewed_img