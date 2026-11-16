from ML.Preprocessing.Crop import Crop
from ML.Preprocessing.ConvertColor import ConvertColor
from ML.Preprocessing.RemoveNoise import RemoveNoise
from ML.Preprocessing.EnhanceContrast import EnhanceContrast
from ML.Preprocessing.Rotate import Rotate
from ML.Preprocessing.FixTilt import FixTilt

class Preprocessing:
    def __init__(self, ops):
        self.ops = ops

    def process(self, img):
        for op in self.ops:
            if op["op"] == "crop":
                img = Crop().apply(img)
            if op["op"] == "convert_color":
                img = ConvertColor(op["params"]).apply(img)
            if op["op"] == "remove_noise":
                img = RemoveNoise(op["params"]).apply(img)
            if op["op"] == "threshold":
                img = EnhanceContrast(op["params"]).apply(img)
            if op["op"] == "rotate":
                img = Rotate(op["params"]).apply(img)
            if op["op"] == "fix_tilt":
                img = FixTilt().apply(img)
            return img