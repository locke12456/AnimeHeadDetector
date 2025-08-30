import os
import sys
from imgutils.detect import detect_heads
sys.path.insert(0, os.path.abspath("./py"))
from base import BaseDetector

class HeadDetector(BaseDetector):
    def detect(self, image_path, model_name="head_detect_v2.0_x_yv11"):
        return detect_heads(image_path, model_name)
    def create_info(self, origin_rect, mask_rect, mode="head"):
        return super().create_info(origin_rect, mask_rect, mode)