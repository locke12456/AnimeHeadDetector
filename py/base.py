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
            "height": self.height
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
    def __init__(self, origin_rect: Rect, mask_rect: Rect, base_filename = "", mode= "", filter=""):
        self.mode = mode
        self.base_filename = base_filename
        if filter != "":
            self.filename = f'{base_filename}_{mode}_{filter}'
        else:
            self.filename = f'{base_filename}_{mode}'
        self.rect_filename = f'{self.filename}'
        self.mask_name = f'{self.filename}_mask'
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
            "mask_rect": self.mask_rect.to_dict()
        }
    def to_json(self):
        return json.dumps(self.to_dict())
    def save_to_file(self, filename):
        with open(filename, 'w') as f:
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
            mode=data.get("mode", "")
        )
    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls.from_dict(data)

class BaseDetector:
    def __init__(self, output='output', width=260, height=340, make_dirs=True):
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
                d = (dx ** 2 + dy ** 2) ** 0.5
                if d >= blur_size:
                    alpha = 0
                else:
                    alpha = int(255 * (1 - d / blur_size))
                pixels[x, y] = alpha
        return fade_mask

    def create_blurred_mask(self, image_path, rect, blur_size):
        img, _, mask, origin_rect = self.create_mask(image_path, rect)
        if blur_size > 0:
            x1, y1, x2, y2 = origin_rect.x1, origin_rect.y1, origin_rect.x2, origin_rect.y2
            fade_mask = self.create_fadeout_mask(img.size, origin_rect, blur_size)
            mask = ImageChops.darker(mask, fade_mask)
            img_w, img_h = img.size
            mask_rect = Rect(
                max(0, origin_rect.x1 + blur_size),
                max(0, origin_rect.y1 + blur_size),
                min(img_w, origin_rect.x2 - blur_size),
                min(img_h, origin_rect.y2 - blur_size)
            )
            origin_rect = Rect(
                max(0, origin_rect.x1 - blur_size),
                max(0, origin_rect.y1 - blur_size),
                min(img_w, origin_rect.x2 + blur_size),
                min(img_h, origin_rect.y2 + blur_size)
            )
        else:
            mask_rect = origin_rect
        self.base_filename = os.path.basename(image_path).split('.')[0]
        info = self.create_info(origin_rect, mask_rect)
        return img, mask, info

    def create_info(self, origin_rect, mask_rect, mode=""):
        info = RectInfo(origin_rect, mask_rect, self.base_filename, mode, self.filter)
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
            best_det = max(result, key=lambda det: det[1] if isinstance(det, tuple) else det.get('score', 0))
            bbox = best_det[0] if isinstance(best_det, tuple) else best_det['bbox']
        return bbox

    def force_rect_crop(self, image_path, result, rect_width, rect_height):
        img = Image.open(image_path)
        image = os.path.basename(image_path)
        if result:
            best_det = max(result, key=lambda det: det[1] if isinstance(det, tuple) else det.get('score', 0))
            bbox = best_det[0] if isinstance(best_det, tuple) else best_det['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            nx1 = max(0, min(img.width - rect_width, cx - rect_width // 2))
            ny1 = max(0, min(img.height - rect_height, cy - rect_height // 2))
            nx2 = nx1 + rect_width
            ny2 = ny1 + rect_height
            if nx2 > img.width:
                nx2 = img.width
                nx1 = img.width - rect_width
            if ny2 > img.height:
                ny2 = img.height
                ny1 = img.height - rect_height
            cropped = img.crop((nx1, ny1, nx2, ny2))
            return cropped, image
        return None, image

    def DetectAndForceRectCrop(self, image_path, rect):
        result = self.detect(image_path)
        cropped, image = self.force_rect_crop(image_path, result, rect, rect)
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

    def Crop(self, image_path, rect, rect_name = None):
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
        image.save(os.path.join(self.output, f'{filename}.png'))

    def load_image(self, image_path):
        return Image.open(image_path)