import cv2


class RemoveNoise:
    def __init__(self, params):
        self.params = params

    def apply(self, img):
        blur_type = self.params.get("blur_type")
        if blur_type is not None:
            if self.params["blur_type"] == "BASIC":
                denoised_img = cv2.blur(img, (self.params["min_kernel_size"], self.params["max_kernel_size"]), cv2.BORDER_DEFAULT)
            elif self.params["blur_type"] == "GAUSSIAN":
                denoised_img = cv2.GaussianBlur(img, (self.params["min_kernel_size"], self.params["max_kernel_size"]), 0, 0, cv2.BORDER_DEFAULT);
            elif self.params["blur_type"] == "MEDIAN":
                denoised_img = cv2.medianBlur(img, (self.params["kernel_size"]))
            else:
                raise ValueError("Unsupported blur")
        else:
            raise ValueError("Unsupported params")
        return denoised_img