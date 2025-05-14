from imgutils.detect import detect_heads
import os
from PIL import Image
class HeadDetector:
    def __init__(self, output='output', width=260, height=340):
        self.output = output
        self.width = width
        self.height = height
        os.makedirs(self.output, exist_ok=True)

    def detect(self, image_path):
        result = detect_heads(image_path, model_name="head_detect_v2.0_x_yv11")
        return result

    def crop(self, image_path, result):
        img = Image.open(image_path)
        image = os.path.basename(image_path)
        width, height = self.width, self.height

        if result:
            best_det = max(result, key=lambda det: det[1] if isinstance(det, tuple) else det.get('score', 0))
            bbox = best_det[0] if isinstance(best_det, tuple) else best_det['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            box_w, box_h = x2 - x1, y2 - y1

            if width < box_w:
                scale = box_w / width
                new_width = int(width * scale)
                new_height = int(height * scale)
            else:
                new_width = box_w
                new_height = box_h

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            nx1 = max(0, cx - new_width // 2)
            ny1 = max(0, cy - new_height // 2)
            nx2 = min(img.width, nx1 + new_width)
            ny2 = min(img.height, ny1 + new_height)
            cropped = img.crop((nx1, ny1, nx2, ny2))

            cropped = cropped.resize((width, height), Image.LANCZOS)
            return cropped, image
        return None, image

    def DetectAndCrop(self, image_path):
        result = self.detect(image_path)
        cropped, image = self.crop(image_path, result)
        if cropped:
            self.save_image(cropped, image)
        print(result)
        return cropped

    def save_image(self, image, filename):
        image.save(os.path.join(self.output, filename))

    def load_image(self, image_path):
        return Image.open(image_path)