import cv2
import numpy as np
import matplotlib.pyplot as plt
from ultralytics import YOLO
import os
import argparse
from skimage.filters import unsharp_mask

## НАСТРОЙКА ОСНОВНЫХ ПАРАМЕТРОВ ##
# путь к модели для сегментации зубов
DEFAULT_MODEL_PATH = 'model/model_rc_segmentation.pt'
# путь для сохранения масок по умолчанию
DEFAULT_MASKS_PATH = 'output'

def preprocess_opg(image):
    """
    Препроцессинг ортопантомограммы для улучшения визуализации кист
    """
    # Сохраняем оригинальные размеры
    original_shape = image.shape
    
    # Конвертация в оттенки серого (если изображение цветное)
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Нормализация интенсивности
    image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
    
    # Применение CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    image = clahe.apply(image)
    
    # Увеличение резкости с помощью unsharp masking
    image = unsharp_mask(image, radius=1, amount=1.5)
    image = (image * 255).astype(np.uint8)
    
    # Медианная фильтрация для уменьшения шума
    image = cv2.medianBlur(image, 3)
    
    # Преобразование обратно в RGB (YOLOv8 ожидает 3-канальные изображения)
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    
    return image

def mask_to_yolo_format(mask, img_width, img_height):
    """
    Преобразование бинарной маски в формат YOLO (нормализованные координаты полигона)
    """
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    yolo_annotations = []
    
    for contour in contours:
        if len(contour) > 2:
            # Упрощаем контур
            epsilon = 0.001 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Нормализуем координаты
            normalized_contour = approx.squeeze() / [img_width, img_height]
            
            # Формируем строку для YOLO
            if len(normalized_contour.shape) == 2:  # Убедимся, что это 2D массив
                yolo_str = "0 " + " ".join([f"{point[0]:.6f} {point[1]:.6f}" for point in normalized_contour])
                yolo_annotations.append(yolo_str)
    
    return yolo_annotations

def process_image(model, image_path, output_dir, apply_preprocessing=True, conf_threshold=0.25):
    """
    Обработка одного изображения: инференс, сохранение результатов и масок
    """
    # Загрузка изображения
    image = cv2.imread(image_path)
    if image is None:
        print(f"Ошибка: Не удалось загрузить изображение {image_path}")
        return
    
    original_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img_height, img_width = original_image.shape[:2]
    
    # Применение препроцессинга, если необходимо
    if apply_preprocessing:
        processed_image = preprocess_opg(original_image.copy())
    else:
        processed_image = original_image.copy()
    
    # Выполнение инференса
    results = model(processed_image, conf=conf_threshold)
    
    # Создание пустой маски для накопления всех масок
    combined_mask = np.zeros((img_height, img_width), dtype=np.uint8)
    
    # Обработка результатов
    yolo_annotations = []
    for result in results:
        if result.masks is not None:
            # Получаем все маски из результата
            masks = result.masks.data.cpu().numpy()
            
            # Накладываем каждую маску на combined_mask
            for mask in masks:
                # Масштабируем маску к размеру изображения
                mask = cv2.resize(mask, (img_width, img_height))
                # Бинаризируем маску
                mask = (mask > 0.5).astype(np.uint8) * 255
                # Добавляем маску к combined_mask
                combined_mask = np.maximum(combined_mask, mask)
                
                # Преобразуем маску в формат YOLO
                annotations = mask_to_yolo_format(mask, img_width, img_height)
                yolo_annotations.extend(annotations)
    
    # Создаем изображение с наложенной маской
    if np.any(combined_mask > 0):
        # Создаем цветную маску (зеленый цвет)
        color_mask = np.zeros_like(original_image)
        color_mask[combined_mask > 0] = [0, 255, 0]  # Зеленый цвет
        
        # Накладываем маску на изображение с прозрачностью
        alpha = 0.3
        masked_image = cv2.addWeighted(original_image, 1, color_mask, alpha, 0)
        
        # Рисуем bounding boxes
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes.data.cpu().numpy()
                for box in boxes:
                    x1, y1, x2, y2, conf, cls = box
                    cv2.rectangle(masked_image, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    cv2.putText(masked_image, f'Киста: {conf:.2f}', (int(x1), int(y1)-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    else:
        masked_image = original_image.copy()
        print(f"На изображении {os.path.basename(image_path)} не обнаружено кист")
    
    # Сохранение результатов
    base_name = os.path.basename(image_path)
    name, ext = os.path.splitext(base_name)
    
    # Сохраняем изображение с маской
    output_image_path = os.path.join(output_dir, f"{name}_masked{ext}")
    cv2.imwrite(output_image_path, cv2.cvtColor(masked_image, cv2.COLOR_RGB2BGR))
    
    # Сохраняем маску отдельно
    if np.any(combined_mask > 0):
        mask_path = os.path.join(output_dir, f"{name}_mask{ext}")
        cv2.imwrite(mask_path, combined_mask)
    
    # Сохраняем аннотации в формате YOLO
    annotation_path = os.path.join(output_dir, f"{name}.txt")
    with open(annotation_path, 'w') as f:
        for annotation in yolo_annotations:
            f.write(annotation + "\n")
    
    print(f"Результаты для {base_name} сохранены в {output_dir}")
    
    return masked_image, combined_mask, yolo_annotations

def main():
    parser = argparse.ArgumentParser(description='Инференс модели YOLOv8 для сегментации кист на ортопантомограммах')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL_PATH, help='Путь к обученной модели YOLOv8')
    parser.add_argument('--input', type=str, required=True, help='Путь к изображению или папке с изображениями')
    parser.add_argument('--output', type=str, default=DEFAULT_MASKS_PATH, help='Папка для сохранения результатов')
    parser.add_argument('--conf', type=float, default=0.25, help='Порог уверенности для детекции')
    parser.add_argument('--no-preprocessing', action='store_true', help='Не применять препроцессинг к изображениям')
    
    args = parser.parse_args()
    
    # Загрузка модели
    model = YOLO(args.model)
    
    # Создание выходной директории
    os.makedirs(args.output, exist_ok=True)
    
    # Определяем, является ли вход файлом или папкой
    if os.path.isfile(args.input):
        # Обработка одного изображения
        process_image(
            model, 
            args.input, 
            args.output, 
            apply_preprocessing=not args.no_preprocessing,
            conf_threshold=args.conf
        )
    elif os.path.isdir(args.input):
        # Обработка всех изображений в папке
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        for file_name in os.listdir(args.input):
            if file_name.lower().endswith(image_extensions):
                image_path = os.path.join(args.input, file_name)
                process_image(
                    model,
                    image_path,
                    args.output,
                    apply_preprocessing=not args.no_preprocessing,
                    conf_threshold=args.conf
                )
    else:
        print(f"Ошибка: {args.input} не является файлом или папкой")
        return

if __name__ == "__main__":
    main()