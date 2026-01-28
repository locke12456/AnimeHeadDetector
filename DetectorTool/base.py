import os
import json
from PIL import Image, ImageDraw, ImageFilter, ImageChops


class Rect:
    def __init__(self, x1: int, y1: int, x2: int, y2: int):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def to_tuple(self):
        return (self.x1, self.y1, self.x2, self.y2)

    def to_dict(self):
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "position": self.position,
            "width": self.width,
            "height": self.height,
        }

    @property
    def position(self):
        return (self.x1, self.y1)

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    @classmethod
    def from_dict(cls, data):
        return cls(data["x1"], data["y1"], data["x2"], data["y2"])


class RectInfo:
    def __init__(
        self, origin_rect: Rect, mask_rect: Rect, base_filename="", mode="", filter=""
    ):
        self.mode = mode
        self.base_filename = base_filename
        if filter != "":
            self.filename = f"{base_filename}_{mode}_{filter}"
        else:
            self.filename = f"{base_filename}_{mode}"
        self.rect_filename = f"{self.filename}"
        self.mask_name = f"{self.filename}_mask"
        self.origin_rect = origin_rect
        self.mask_rect = mask_rect

    def to_dict(self):
        return {
            "base_filename": self.base_filename,
            "filename": self.filename,
            "rect_filename": self.rect_filename,
            "mask_name": self.mask_name,
            "mode": self.mode,
            "origin_rect": self.origin_rect.to_dict(),
            "mask_rect": self.mask_rect.to_dict(),
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def save_to_file(self, filename):
        with open(filename, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def from_dict(cls, data):
        return cls(
            filename=data.get("filename", ""),
            rect_filename=data.get("rect_filename", ""),
            mask_name=data.get("mask_name", ""),
            origin_rect=Rect.from_dict(data["origin_rect"]),
            mask_rect=Rect.from_dict(data["mask_rect"]),
            base_filename=data.get("base_filename", ""),
            mode=data.get("mode", ""),
        )

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls.from_dict(data)


class BaseDetector:
    def __init__(self, output="output", width=260, height=340, make_dirs=True):
        self.output = output
        self.width = width
        self.height = height
        self.filter = ""
        if make_dirs and not os.path.exists(self.output):
            os.makedirs(self.output, exist_ok=True)

    def create_blurred_alpha_mask(self, image_path, rect, blur_size):
        img, origin_alpha, mask, _ = self.create_mask(image_path, rect)
        mask = Image.composite(origin_alpha, mask, mask)
        if blur_size > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(blur_size))
        img.putalpha(mask)
        return img, mask

    def create_fadeout_mask(self, mask_size, origin_rect, blur_size):
        x1, y1, x2, y2 = origin_rect.x1, origin_rect.y1, origin_rect.x2, origin_rect.y2
        fade_mask = Image.new("L", mask_size, 0)
        pixels = fade_mask.load()
        for y in range(y1, y2):
            for x in range(x1, x2):
                dx = 0
                if x < x1 + blur_size:
                    dx = x1 + blur_size - x
                elif x > x2 - blur_size - 1:
                    dx = x - (x2 - blur_size - 1)
                dy = 0
                if y < y1 + blur_size:
                    dy = y1 + blur_size - y
                elif y > y2 - blur_size - 1:
                    dy = y - (y2 - blur_size - 1)
                d = (dx**2 + dy**2) ** 0.5
                if d >= blur_size:
                    alpha = 0
                else:
                    alpha = int(255 * (1 - d / blur_size))
                pixels[x, y] = alpha
        return fade_mask

    # [修改] 增加 index 參數
    def create_blurred_mask(self, image_path, rect, blur_size, index=None):
        img, _, mask, origin_rect = self.create_mask(image_path, rect)
        if blur_size > 0:
            x1, y1, x2, y2 = (
                origin_rect.x1,
                origin_rect.y1,
                origin_rect.x2,
                origin_rect.y2,
            )
            fade_mask = self.create_fadeout_mask(img.size, origin_rect, blur_size)
            mask = ImageChops.darker(mask, fade_mask)
            img_w, img_h = img.size
            mask_rect = Rect(
                max(0, origin_rect.x1 + blur_size),
                max(0, origin_rect.y1 + blur_size),
                min(img_w, origin_rect.x2 - blur_size),
                min(img_h, origin_rect.y2 - blur_size),
            )
            origin_rect = Rect(
                max(0, origin_rect.x1 - blur_size),
                max(0, origin_rect.y1 - blur_size),
                min(img_w, origin_rect.x2 + blur_size),
                min(img_h, origin_rect.y2 + blur_size),
            )
        else:
            mask_rect = origin_rect
        self.base_filename = os.path.basename(image_path).split(".")[0]
        # [修改] 傳遞 index 參數
        info = self.create_info(origin_rect, mask_rect, index=index)
        return img, mask, info

    # [修改] 增加 index 參數
    def create_info(self, origin_rect, mask_rect, mode="", index=None):
        suffix = f"_{index}" if index is not None else ""
        info = RectInfo(origin_rect, mask_rect, self.base_filename + suffix, mode, self.filter)
        return info

    def create_mask(self, image_path, rect):
        image = Image.open(image_path)
        if image.mode != "RGBA":
            img = image.convert("RGBA")
        else:
            img = image.copy()
        if "A" in img.getbands():
            origin_alpha = img.split()[-1]
        else:
            origin_alpha = Image.new("L", img.size, 255)
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        x1, y1, x2, y2 = rect
        draw.rectangle([x1, y1, x2, y2], fill=255)
        origin_rect = Rect(x1, y1, x2, y2)
        return img, origin_alpha, mask, origin_rect

    def crop(self, image_path, result, bbox=None):
        img = Image.open(image_path)
        image = os.path.basename(image_path)
        width, height = self.width, self.height
        if result:
            if bbox is not None:
                x1, y1, x2, y2 = map(int, bbox)
                cropped = img.crop((x1, y1, x2, y2))
                return cropped, image, bbox
            bbox = self.get_best_rect(result)
            x1, y1, x2, y2 = map(int, bbox)
            box_w, box_h = x2 - x1, y2 - y1
            if width < box_w:
                scale = box_w / width
                new_width = int(width * scale)
                new_height = int(height * scale)
            else:
                new_width = box_w
                new_height = box_h
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            crop_start_x = max(0, center_x - new_width // 2)
            crop_start_y = max(0, center_y - new_height // 2)
            crop_end_x = min(img.width, crop_start_x + new_width)
            crop_end_y = min(img.height, crop_start_y + new_height)
            cropped = img.crop((crop_start_x, crop_start_y, crop_end_x, crop_end_y))
            cropped = cropped.resize((width, height), Image.LANCZOS)
            return cropped, image, bbox
        return None, image, None

    def get_best_rect(self, result, filter_label=None):
        if filter_label is not None:
            self.filter = filter_label
        if filter_label:
            filtered = [r for r in result if r[1] == filter_label]
            if not filtered:
                return None
            best_det = max(filtered, key=lambda r: r[2])
            bbox = best_det[0]
        else:
            best_det = max(
                result,
                key=lambda det: (
                    det[1] if isinstance(det, tuple) else det.get("score", 0)
                ),
            )
            bbox = best_det[0] if isinstance(best_det, tuple) else best_det["bbox"]
        return bbox

    # [新增] 回傳前 N 個結果的 bbox 列表
    def get_top_rects(self, result, filter_label=None, top_n=3):
        """回傳前 N 個結果的 bbox 列表"""
        if filter_label is not None:
            self.filter = filter_label
        if filter_label:
            filtered = [r for r in result if r[1] == filter_label]
            if not filtered:
                return []
            sorted_dets = sorted(filtered, key=lambda r: r[2], reverse=True)[:top_n]
            return [det[0] for det in sorted_dets]
        else:
            sorted_dets = sorted(
                result,
                key=lambda det: (det[1] if isinstance(det, tuple) else det.get("score", 0)),
                reverse=True
            )[:top_n]
            return [det[0] if isinstance(det, tuple) else det["bbox"] for det in sorted_dets]

    def force_rect_crop(
        self,
        image_path,
        detections,
        crop_width,
        crop_height,
        resize=False,
        bg_path=None,
    ):
        """
        以最高分數偵測框為中心裁切。
        - 若目標尺寸小於偵測框，先把裁切尺寸擴大到至少覆蓋偵測框（desired_w/h）。
        - 若裁切框超出原圖邊界，先對原圖做「邊界補償」再裁切，避免出現空白帶。
        - resize=True 時，等比縮放並以背景補邊到精確 (crop_width, crop_height)。
        - bg_path 提供背景圖時，會將裁切結果合成到背景上（僅支援 PNG 格式）。
        """
        source_image = Image.open(image_path)
        filename = os.path.basename(image_path).split(".")[0]
        
        if not detections:
            return None, filename
        
        # 最高分偵測
        best_detection = max(detections, key=lambda d: d[1] if isinstance(d, tuple) else d.get("score", 0))
        detection_bbox = best_detection[0] if isinstance(best_detection, tuple) else best_detection["bbox"]
        bbox_left, bbox_top, bbox_right, bbox_bottom = map(int, detection_bbox)
        
        # 偵測中心 + 正方形邊長 square_size = max(bbox_width, bbox_height)
        detection_center_x = (bbox_left + bbox_right) // 2
        detection_center_y = (bbox_top + bbox_bottom) // 2
        bbox_width = max(1, bbox_right - bbox_left)
        bbox_height = max(1, bbox_bottom - bbox_top)
        square_size = max(bbox_width, bbox_height)
        
        # 以中心置中的 square_size×square_size 視窗
        crop_left = detection_center_x - square_size // 2
        crop_top = detection_center_y - square_size // 2
        crop_right = crop_left + square_size
        crop_bottom = crop_top + square_size
        
        # 只用座標平移把視窗夾回圖內（不擴邊）
        if crop_left < 0:
            crop_right -= crop_left
            crop_left = 0
        if crop_top < 0:
            crop_bottom -= crop_top
            crop_top = 0
        if crop_right > source_image.width:
            boundary_shift = crop_right - source_image.width
            crop_left -= boundary_shift
            crop_right = source_image.width
        if crop_bottom > source_image.height:
            boundary_shift = crop_bottom - source_image.height
            crop_top -= boundary_shift
            crop_bottom = source_image.height
        
        # 保險夾取（保持正方形尺寸 square_size×square_size）
        crop_left = max(0, min(crop_left, source_image.width - square_size))
        crop_top = max(0, min(crop_top, source_image.height - square_size))
        crop_right = crop_left + square_size
        crop_bottom = crop_top + square_size
        
        # 先剪取 square_size×square_size
        cropped_image = source_image.crop((int(crop_left), int(crop_top), int(crop_right), int(crop_bottom)))
        
        # 再 resize 到 crop_width×crop_height
        if resize:
            if cropped_image.width != crop_width or cropped_image.height != crop_height:
                cropped_image = cropped_image.resize((crop_width, crop_height), Image.Resampling.LANCZOS)
        
        # 背景圖片合成處理
        if bg_path:
            try:
                background_image = Image.open(bg_path)
                
                # 如果背景圖片尺寸不匹配，強制 resize
                if background_image.width != crop_width or background_image.height != crop_height:
                    background_image = background_image.resize((crop_width, crop_height), Image.Resampling.LANCZOS)
                
                # 檢查裁切圖片是否為 PNG 格式（有透明通道）
                if cropped_image.mode in ('RGBA', 'LA') or 'transparency' in cropped_image.info:
                    # 確保背景圖片也有 alpha 通道
                    if background_image.mode != 'RGBA':
                        background_image = background_image.convert('RGBA')
                    if cropped_image.mode != 'RGBA':
                        cropped_image = cropped_image.convert('RGBA')
                    
                    # 將裁切圖片合成到背景上
                    final_image = Image.alpha_composite(background_image, cropped_image)
                    return final_image, filename
                else:
                    # 非 PNG 格式，跳過合成
                    return cropped_image, filename
                    
            except Exception as e:
                print(f"背景圖片處理失敗: {e}")
                return cropped_image, filename
        
        return cropped_image, filename
    
    def DetectAndForceRectCrop(self, image_path, rect, resize=False, bg_path=None):
        result = self.detect(image_path)
        cropped, image = self.force_rect_crop(image_path, result, rect, rect, resize, bg_path)
        if cropped:
            self.save_image(cropped, image)
        print(result)
        return cropped

    def DetectAndCrop(self, image_path):
        result = self.detect(image_path)
        cropped, image, bbox = self.crop(image_path, result)
        if cropped:
            self.save_image(cropped, image)
        print(result)
        return cropped, image, bbox

    def Detect(self, image_path):
        result = self.detect(image_path)
        bbox = self.get_best_rect(result)
        return bbox

    def Crop(self, image_path, rect, rect_name=None):
        img = Image.open(image_path)
        if not rect_name:
            image = os.path.basename(image_path)
        else:
            image = rect_name
        x1, y1, x2, y2 = map(int, rect)
        cropped = img.crop((x1, y1, x2, y2))
        self.save_image(cropped, image)
        return cropped, image

    def save_image(self, image, filename):
        image.save(os.path.join(self.output, f"{filename}.png"))

    def load_image(self, image_path):
        return Image.open(image_path)