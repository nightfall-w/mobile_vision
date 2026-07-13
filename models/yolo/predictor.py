import os
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont


class YOLOPredictor:
    def __init__(self, model_path, class_names_from_db=None):
        self.model = YOLO(model_path)
        self.class_names = self.model.names if hasattr(self.model, 'names') else {}
        # 优先使用数据库中的 classes 作为显示名称
        self.db_class_names = class_names_from_db or []
        if self.db_class_names:
            # 优先取 chinese，没有则取 english，兜底转字符串
            self._display_names = {}
            for i, cls in enumerate(self.db_class_names):
                if isinstance(cls, dict):
                    self._display_names[i] = cls.get('chinese') or cls.get('english') or str(cls)
                else:
                    self._display_names[i] = str(cls)
        else:
            self._display_names = self.class_names

    def predict(self, image_path, conf_threshold=0.15, save_result=False, output_dir='./output'):
        # 先验证图像文件是否可读
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")

        try:
            img = Image.open(image_path)
            img.verify()  # 验证图像是否有效
            img = Image.open(image_path)  # 重新打开因为verify()会关闭文件
        except Exception as e:
            raise ValueError(f"图像文件无法读取: {image_path}, 错误: {str(e)}")

        results = self.model.predict(
            source=str(image_path),
            conf=conf_threshold,
            save=False,
            verbose=False
        )

        predictions = []
        img_width, img_height = img.size

        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                cls = int(box.cls[0].cpu().numpy())
                class_name = self._display_names.get(cls, self.class_names.get(cls, f'class_{cls}'))

                x_center = ((x1 + x2) / 2) / img_width
                y_center = ((y1 + y2) / 2) / img_height
                width = (x2 - x1) / img_width
                height = (y2 - y1) / img_height

                predictions.append({
                    'class_id': cls,
                    'class_name': class_name,
                    'confidence': float(conf),
                    'bbox': {
                        'x1': float(x1),
                        'y1': float(y1),
                        'x2': float(x2),
                        'y2': float(y2)
                    },
                    'x_center': float(x_center),
                    'y_center': float(y_center),
                    'width': float(width),
                    'height': float(height)
                })

        if save_result and results:
            os.makedirs(output_dir, exist_ok=True)
            self._draw_and_save(image_path, results[0], output_dir)

        return predictions

    @staticmethod
    def _get_color(class_id: int) -> tuple:
        """根据类别ID返回不同颜色"""
        colors = [
            (255, 0, 0),  # 红
            (0, 150, 255),  # 橙
            (0, 200, 0),  # 绿
            (255, 0, 150),  # 粉
            (0, 100, 255),  # 蓝
            (255, 200, 0),  # 黄
            (150, 0, 255),  # 紫
            (0, 200, 200),  # 青
            (200, 100, 0),  # 棕
            (100, 200, 100),  # 浅绿
        ]
        return colors[class_id % len(colors)]

    def _draw_and_save(self, image_path, result, output_dir):
        image = Image.open(image_path).convert('RGB')
        draw = ImageDraw.Draw(image)

        # 使用中文字体
        font_size = 22
        font = None
        chinese_font_paths = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        ]
        for fp in chinese_font_paths:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except:
                    continue
        if font is None:
            try:
                font = ImageFont.truetype('/System/Library/Fonts/SFNSDisplay.ttf', font_size)
            except:
                font = ImageFont.load_default()

        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = box.conf[0].cpu().numpy()
            cls = int(box.cls[0].cpu().numpy())
            display_name = self._display_names.get(cls, self.class_names.get(cls, f'class_{cls}'))
            color = self._get_color(cls)

            # 绘制边框（加粗）
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)

            # 绘制标签背景和文字
            text = f'{display_name}: {conf:.2f}'
            text_bbox = draw.textbbox((x1, y1 - font_size - 4), text, font=font)
            label_h = text_bbox[3] - text_bbox[1]
            label_w = text_bbox[2] - text_bbox[0]
            draw.rectangle([(x1, y1 - label_h - 4), (x1 + label_w + 8, y1)], fill=color)
            draw.text((x1 + 4, y1 - label_h - 4), text, fill='white', font=font)

        output_path = os.path.join(output_dir, os.path.basename(image_path))
        image.save(output_path)
        print(f'检测结果已保存到: {output_path}')


def main(model_path, image_path):
    predictor = YOLOPredictor(
        model_path=model_path
    )

    predictions = predictor.predict(
        image_path=image_path,
        conf_threshold=0.25,
        save_result=True,
        output_dir="./output"
    )

    for pred in predictions:
        print(f"类别: {pred['class_name']}, 置信度: {pred['confidence']}")


if __name__ == "__main__":
    main(model_path="/Users/baojunw/Desktop/毕设/mobile_vision/models/yolo/runs/detect/train4/weights/best.pt",
         image_path="/Users/baojunw/Downloads/Snipaste_2026-04-25_23-18-21.png")
