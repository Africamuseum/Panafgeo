import cv2

class EnhanceContrast:
    def __init__(self, params):
        self.params = params

    def apply(self, img):
        # Apply thresholding
        value = self.params.get("value")
        maxval = self.params.get("maxval")
        threshold_method = self.params.get("threshold_method")
        threshold_type = self.params.get("threshold_type")
        if value is not None and maxval is not None and \
            threshold_method is not None and threshold_type is not None:
            if threshold_method == "GLOBAL" and threshold_type == "BINARY":
                ret, contrasted_img = cv2.threshold(img, value, maxval, cv2.THRESH_BINARY)
            elif threshold_method == "GLOBAL" and threshold_type == "BINARY_INV":
                ret, contrasted_img = cv2.threshold(img, value, maxval, cv2.THRESH_BINARY_INV)
            elif threshold_method == "GLOBAL" and threshold_type == "TRUNC":
                ret, contrasted_img = cv2.threshold(img, value, maxval, cv2.THRESH_TRUNC)
            elif threshold_method == "GLOBAL" and threshold_type == "TOZERO":
                ret, contrasted_img = cv2.threshold(img, value, 0, cv2.THRESH_TOZERO)
            elif threshold_method == "GLOBAL" and threshold_type == "TOZERO_INV":
                ret, contrasted_img = cv2.threshold(img, value, 0, cv2.THRESH_TOZERO_INV)
            elif threshold_method == "GLOBAL" and threshold_type == "BINARY + OTSU":
                ret, contrasted_img = cv2.threshold(img, 0, value, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            elif threshold_method == "GLOBAL" and threshold_type == "BINARY_INV + OTSU":
                ret, contrasted_img = cv2.threshold(img, 0, value, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            elif threshold_method == "GLOBAL" and threshold_type == "TRUNC + OTSU":
                ret, contrasted_img = cv2.threshold(img, 0, value, cv2.THRESH_TRUNC + cv2.THRESH_OTSU)
            elif threshold_method == "GLOBAL" and threshold_type == "TOZERO + OTSU":
                ret, contrasted_img = cv2.threshold(img, 0, 0, cv2.THRESH_TOZERO + cv2.THRESH_OTSU)
            elif threshold_method == "GLOBAL" and threshold_type == "TOZERO_INV + OTSU":
                ret, contrasted_img = cv2.threshold(img, 0, 0, cv2.THRESH_TOZERO_INV + cv2.THRESH_OTSU)
            elif threshold_method == "ADAPTIVE_MEAN" and threshold_type == "BINARY":
                contrasted_img = cv2.adaptiveThreshold(img, value, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, self.params["block_size"], self.params["C"])
            elif threshold_method == "ADAPTIVE_MEAN" and threshold_type == "BINARY_INV":
                contrasted_img = cv2.adaptiveThreshold(img, value, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, self.params["block_size"], self.params["C"])
            elif threshold_method == "ADAPTIVE_GAUSSIAN" and threshold_type == "BINARY":
                contrasted_img = cv2.adaptiveThreshold(img, value, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, self.params["block_size"], self.params["C"])
            elif threshold_method == "ADAPTIVE_GAUSSIAN" and threshold_type == "BINARY_INV":
                contrasted_img = cv2.adaptiveThreshold(img, value, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, self.params["block_size"], self.params["C"])
            else:
                raise ValueError("Unsupported threshold")
        else:
            raise ValueError("Unsupported params")
        return contrasted_img