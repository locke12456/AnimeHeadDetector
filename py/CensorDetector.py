import os
import sys
from imgutils.detect import detect_heads, detect_censors
sys.path.insert(0, os.path.abspath("./py"))
from base import BaseDetector

class CensorDetector(BaseDetector):
    def detect(self, image_path, model_name="censor_detect_v1.0_s"):
        return detect_censors(image_path, model_name=model_name, )
    def create_info(self, origin_rect, mask_rect, mode="censor"):
        return super().create_info(origin_rect, mask_rect, mode)