import os
import sys
from imgutils.detect import detect_heads, detect_censors

from .base import BaseDetector

class CensorDetector(BaseDetector):
    def detect(self, image_path, model_name="censor_detect_v1.0_s"):
        return detect_censors(image_path, model_name=model_name, )
    
    # [修改] 增加 index 參數並傳遞給 super()
    def create_info(self, origin_rect, mask_rect, mode="censor", index=None):
        return super().create_info(origin_rect, mask_rect, mode, index=index)