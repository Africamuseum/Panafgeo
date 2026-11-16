import cv2

class ConvertColor:
    def __init__(self, params):
        self.params = params

    def apply(self, img):
        # Convert the image to the specified color space
        if len(img.shape) != 2:
            if self.params["color_space"] == "GRAY":
                converted_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            elif self.params["color_space"] == "RGB":
                converted_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            elif self.params["color_space"] == "HSV":
                converted_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            else:
                raise ValueError("Unsupported color space")
        else:
            return img
        return converted_img