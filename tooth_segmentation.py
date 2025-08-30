import cv2
import numpy as np
import argparse
from pathlib import Path
import sys

## НАСТРОЙКА ОСНОВНЫХ ПАРАМЕТРОВ ##
# путь к модели для сегментации зубов
DEFAULT_MODEL_PATH = 'model/model_tooth_segmentation.pt'
# путь для сохранения масок по умолчанию
DEFAULT_MASKS_PATH = 'output'


try:
    from ultralytics import YOLO
except ImportError:
    print("Ошибка: Не удалось импортировать ultralytics. Установите его с помощью: pip install ultralytics")
    sys.exit(1)

def preprocess_image(image):
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image

    gray = gray.copy()
    gray[gray > 200] = np.median(gray)
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB).astype(np.float32) / 255.0
    return enhanced_rgb

def class_id_to_fdi(class_id):
    """
    Преобразует идентификатор класса от 0 до 31 в обозначение FDI-ISO
    """
    fdi_mapping = {
        0: 11, 1: 12, 2: 13, 3: 14, 4: 15, 5: 16, 6: 17, 7: 18,
        8: 21, 9: 22, 10: 23, 11: 24, 12: 25, 13: 26, 14: 27, 15: 28,
        16: 31, 17: 32, 18: 33, 19: 34, 20: 35, 21: 36, 22: 37, 23: 38,
        24: 41, 25: 42, 26: 43, 27: 44, 28: 45, 29: 46, 30: 47, 31: 48
    }
    
    return fdi_mapping.get(class_id, f"unknown_{class_id}")

def create_combined_mask(masks, class_ids, image_shape):
    """
    Создает единое изображение со всеми масками, где каждый зуб имеет свой цвет.
    Также создает легенду с номерами FDI.
    """
    # Создаем пустое изображение для комбинированной маски
    combined = np.zeros((image_shape[0], image_shape[1], 3), dtype=np.uint8)
    
    # Генерируем уникальные цвета для каждого класса
    np.random.seed(42)  # Для воспроизводимости результатов
    colors = {}
    
    for i, (mask, class_id) in enumerate(zip(masks, class_ids)):
        # Масштабируем маску к исходному размеру
        mask_resized = cv2.resize(mask, (image_shape[1], image_shape[0]))
        mask_bool = (mask_resized > 0.5)
        
        # Генерируем или получаем цвет для этого класса
        if class_id not in colors:
            colors[class_id] = tuple(np.random.randint(50, 256, 3).tolist())
        
        # Добавляем маску на комбинированное изображение
        combined[mask_bool] = colors[class_id]
    
    # Создаем легенду
    legend_height = 50 + len(colors) * 30
    legend = np.ones((legend_height, 300, 3), dtype=np.uint8) * 255
    
    # Добавляем заголовок
    cv2.putText(legend, "FDI Numbers", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # Добавляем цветные квадраты и подписи
    for i, (class_id, color) in enumerate(colors.items()):
        y_pos = 60 + i * 30
        fdi_number = class_id_to_fdi(class_id)
        
        # Рисуем цветной квадрат
        cv2.rectangle(legend, (10, y_pos - 15), (30, y_pos + 5), color, -1)
        
        # Добавляем текст с номером FDI
        cv2.putText(legend, str(fdi_number), (40, y_pos), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    # Объединяем основное изображение и легенду
    if combined.shape[0] > legend_height:
        # Если основное изображение выше легенды, добавляем легенду справа
        legend_resized = cv2.resize(legend, (300, combined.shape[0]))
        combined_with_legend = np.hstack([combined, legend_resized])
    else:
        # Если легенда выше, добавляем ее снизу
        legend_width = min(combined.shape[1], 600)
        legend_resized = cv2.resize(legend, (legend_width, legend_height))
        combined_with_legend = np.vstack([combined, legend_resized])
    
    return combined_with_legend

def mask_to_yolo_polygon(mask, img_width, img_height):
    """
    Преобразует бинарную маску в полигон в формате YOLO.
    Возвращает строку с нормализованными координатами полигона.
    """
    # Находим контуры в маске
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    # Выбираем контур с наибольшей площадью
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Упрощаем контур (уменьшаем количество точек)
    epsilon = 0.002 * cv2.arcLength(largest_contour, True)
    simplified_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    # Нормализуем координаты относительно размеров изображения
    normalized_coords = []
    for point in simplified_contour:
        x = point[0][0] / img_width
        y = point[0][1] / img_height
        normalized_coords.append(f"{x:.6f}")
        normalized_coords.append(f"{y:.6f}")
    
    return " ".join(normalized_coords)

def save_yolo_annotations(masks, class_ids, img_width, img_height, output_path):
    """
    Сохраняет аннотации в формате YOLO.
    Каждая строка соответствует одному объекту: class_id x1 y1 x2 y2 ... xn yn
    """
    with open(output_path, 'w') as f:
        for mask, class_id in zip(masks, class_ids):
            # Масштабируем маску к исходному размеру
            mask_resized = cv2.resize(mask, (img_width, img_height))
            mask_binary = (mask_resized > 0.5).astype(np.uint8)
            
            # Преобразуем маску в полигон YOLO
            polygon = mask_to_yolo_polygon(mask_binary, img_width, img_height)
            
            if polygon:
                f.write(f"{class_id} {polygon}\n")

def main():
    parser = argparse.ArgumentParser(description='YOLOv8 зубная сегментация')
    parser.add_argument('--image', type=str, required=True, help='Путь к входному изображению')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL_PATH, help='Путь к модели YOLOv8')
    parser.add_argument('--output', type=str, default=DEFAULT_MASKS_PATH, help='Директория для сохранения результатов')
    args = parser.parse_args()

    # Проверяем существование файла изображения
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Ошибка: Файл {args.image} не существует")
        sys.exit(1)

    # Проверяем существование файла модели
    if not Path(args.model).exists():
        print(f"Ошибка: Файл модели {args.model} не существует")
        sys.exit(1)

    # Создаем директорию для результатов
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    try:
        # Загружаем модель
        model = YOLO(args.model)
        
        # Загружаем и обрабатываем изображение
        orig = cv2.imread(str(image_path))
        if orig is None:
            print(f"Ошибка: Не удалось загрузить изображение {args.image}")
            sys.exit(1)
            
        orig_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
        proc = preprocess_image(orig_rgb)
        proc_uint8 = (proc * 255).astype(np.uint8)

        # Выполняем инференс
        results = model.predict(proc_uint8, verbose=False)[0]

        # Сохраняем маски
        if results.masks is not None:
            masks = results.masks.data.cpu().numpy()
            class_ids = results.boxes.cls.cpu().numpy().astype(int)
            
            # Сохраняем отдельные маски
            for i, (mask, class_id) in enumerate(zip(masks, class_ids)):
                # Масштабируем маску к исходному размеру
                mask_resized = cv2.resize(mask, (orig.shape[1], orig.shape[0]))
                # Бинаризуем маску
                mask_binary = (mask_resized > 0.5).astype(np.uint8) * 255
                
                # Преобразуем идентификатор класса в обозначение FDI-ISO
                fdi_number = class_id_to_fdi(class_id)
                
                # Сохраняем маску
                mask_name = f"tooth_{i+1}_FDI_{fdi_number}.png"
                cv2.imwrite(str(output_dir / mask_name), mask_binary)
                
            print(f"Сохранино {len(masks)} отдельных масок в директорию {output_dir}")
            
            # Создаем и сохраняем комбинированную маску
            combined_mask = create_combined_mask(masks, class_ids, orig.shape[:2])
            cv2.imwrite(str(output_dir / "all_masks_combined.png"), combined_mask)
            print("Комбинированная маска со всеми зубами сохранена как all_masks_combined.png")
            
            # Сохраняем аннотации в формате YOLO
            yolo_output_path = output_dir / f"{image_path.stem}_yolo.txt"
            save_yolo_annotations(masks, class_ids, orig.shape[1], orig.shape[0], str(yolo_output_path))
            print(f"Аннотации YOLO сохранены в файл {yolo_output_path.name}")
            
            # Дополнительно: сохраняем изображение с аннотациями
            annotated_img = orig_rgb.copy()
            for i, (mask, class_id) in enumerate(zip(masks, class_ids)):
                mask_resized = cv2.resize(mask, (orig.shape[1], orig.shape[0]))
                mask_bool = (mask_resized > 0.5)
                
                # Находим центр масс маски
                y, x = np.where(mask_bool)
                if len(x) > 0 and len(y) > 0:
                    center_x, center_y = int(np.mean(x)), int(np.mean(y))
                    fdi_number = class_id_to_fdi(class_id)
                    
                    # Добавляем текст с номером FDI
                    cv2.putText(annotated_img, str(fdi_number), 
                                (center_x, center_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            # Сохраняем аннотированное изображение
            annotated_img_bgr = cv2.cvtColor(annotated_img, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(output_dir / "annotated_image.jpg"), annotated_img_bgr)
            print(f"Аннотированное изображение сохранено как annotated_image.jpg")
            
        else:
            print("Маски не обнаружены")
            
    except Exception as e:
        print(f"Произошла ошибка при обработке изображения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()