import cv2


class Rotate:
    def __init__(self, params):
        self.params = params

    def apply(self, img):
        if self.params["degree"] == -90 or self.params["degree"] == 270:
            rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif self.params["degree"] == 90 or self.params["degree"] == -270:
            rotated_img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.params["degree"] == 180 or self.params["degree"] == -180:
            rotated_img = cv2.rotate(img, cv2.ROTATE_180)
        elif self.params["degree"] == 0:
            return img
        else:
            raise ValueError("Unsupported rotation direction")
        return rotated_img