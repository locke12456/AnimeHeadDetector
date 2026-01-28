import os
import sys
from imgutils.detect import detect_heads

from .base import BaseDetector

class HeadDetector(BaseDetector):
    def detect(self, image_path, model_name="head_detect_v2.0_x_yv11"):
        return detect_heads(image_path, model_name)
    
    # [修改] 增加 index 參數並傳遞給 super()
    def create_info(self, origin_rect, mask_rect, mode="head", index=None):
        return super().create_info(origin_rect, mask_rect, mode, index=index)