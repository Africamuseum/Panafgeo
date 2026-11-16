import cv2


class Range:
    def __init__(self, params):
        self.params = params

    def apply(self, img):
        ranged_img = cv2.inRange(img, self.params["lower_bound"], self.params["upper_bound"])
        return ranged_img