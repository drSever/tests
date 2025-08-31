#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для анализа стоматологических изображений
Содержит функции для работы с сегментацией зубов и кист
"""

import cv2
import numpy as np
import os
from typing import Tuple, List, Optional
import matplotlib.pyplot as plt
from ultralytics import YOLO


def replace_cyst_volume(image_path: str, 
                       mask_path: str, 
                       output_path: str,
                       replacement_method: str = "interpolation",
                       fill_color: Tuple[int, int, int] = (255, 255, 255)) -> bool:
    """
    Заменяет объём кисты на изображении различными методами
    
    Args:
        image_path (str): Путь к исходному изображению
        mask_path (str): Путь к маске кисты
        output_path (str): Путь для сохранения результата
        replacement_method (str): Метод замены ('interpolation', 'blur', 'color_fill')
        fill_color (tuple): Цвет для заполнения (RGB) при методе 'color_fill'
    
    Returns:
        bool: True если операция выполнена успешно, False иначе
    """
    try:
        # Загружаем изображение и маску
        image = cv2.imread(image_path)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        
        if image is None or mask is None:
            print(f"Ошибка: Не удалось загрузить изображение или маску")
            return False
        
        # Создаём копию изображения для работы
        result_image = image.copy()
        
        # Находим контуры кисты
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print("Предупреждение: Не найдено контуров кисты в маске")
            return False
        
        # Обрабатываем каждый контур кисты
        for contour in contours:
            # Создаём маску для текущего контура
            contour_mask = np.zeros_like(mask)
            cv2.fillPoly(contour_mask, [contour], 255)
            
            # Находим границы области кисты
            x, y, w, h = cv2.boundingRect(contour)
            
            if replacement_method == "interpolation":
                # Метод интерполяции - заполняем область интерполированными значениями
                result_image = _interpolate_cyst_area(result_image, contour_mask, x, y, w, h)
                
            elif replacement_method == "blur":
                # Метод размытия - размываем область кисты
                result_image = _blur_cyst_area(result_image, contour_mask, x, y, w, h)
                
            elif replacement_method == "color_fill":
                # Метод заполнения цветом
                result_image = _fill_cyst_area(result_image, contour_mask, fill_color)
                
            else:
                print(f"Неизвестный метод замены: {replacement_method}")
                return False
        
        # Сохраняем результат
        cv2.imwrite(output_path, result_image)
        print(f"Объём кисты успешно заменён. Результат сохранён в: {output_path}")
        return True
        
    except Exception as e:
        print(f"Ошибка при замене объёма кисты: {str(e)}")
        return False


def _interpolate_cyst_area(image: np.ndarray, 
                          mask: np.ndarray, 
                          x: int, y: int, 
                          w: int, h: int) -> np.ndarray:
    """
    Заполняет область кисты интерполированными значениями
    """
    result = image.copy()
    
    # Расширяем область для лучшей интерполяции
    padding = 10
    x_start = max(0, x - padding)
    y_start = max(0, y - padding)
    x_end = min(image.shape[1], x + w + padding)
    y_end = min(image.shape[0], y + h + padding)
    
    # Создаём маску для интерполяции
    interp_mask = mask[y_start:y_end, x_start:x_end]
    
    # Для каждого канала выполняем интерполяцию
    for channel in range(3):
        channel_data = image[y_start:y_end, x_start:x_end, channel]
        
        # Создаём сетку координат
        rows, cols = channel_data.shape
        grid_x, grid_y = np.meshgrid(np.arange(cols), np.arange(rows))
        
        # Находим точки вне маски для интерполяции
        valid_points = interp_mask == 0
        if np.sum(valid_points) > 0:
            # Интерполируем значения
            from scipy.interpolate import griddata
            
            points = np.column_stack([grid_y[valid_points], grid_x[valid_points]])
            values = channel_data[valid_points]
            
            # Создаём точки для интерполяции (внутри маски)
            interp_points = np.column_stack([grid_y[interp_mask > 0], grid_x[interp_mask > 0]])
            
            if len(interp_points) > 0:
                # Выполняем интерполяцию
                interpolated = griddata(points, values, interp_points, method='linear', fill_value=np.mean(values))
                
                # Заполняем область кисты
                channel_data[interp_mask > 0] = interpolated
                result[y_start:y_end, x_start:x_end, channel] = channel_data
    
    return result


def _blur_cyst_area(image: np.ndarray, 
                   mask: np.ndarray, 
                   x: int, y: int, 
                   w: int, h: int) -> np.ndarray:
    """
    Размывает область кисты
    """
    result = image.copy()
    
    # Применяем размытие к области кисты
    kernel_size = min(w, h) // 10 + 1
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    # Размываем изображение
    blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    # Заменяем область кисты размытым изображением
    result[mask > 0] = blurred[mask > 0]
    
    return result


def _fill_cyst_area(image: np.ndarray, 
                   mask: np.ndarray, 
                   fill_color: Tuple[int, int, int]) -> np.ndarray:
    """
    Заполняет область кисты указанным цветом
    """
    result = image.copy()
    
    # Заполняем область кисты указанным цветом
    result[mask > 0] = fill_color
    
    return result


def analyze_cyst_volume(mask_path: str) -> dict:
    """
    Анализирует объём кисты по маске
    
    Args:
        mask_path (str): Путь к маске кисты
    
    Returns:
        dict: Словарь с информацией о кисте
    """
    try:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        
        if mask is None:
            return {"error": "Не удалось загрузить маску"}
        
        # Находим контуры
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {"error": "Не найдено контуров кисты"}
        
        # Анализируем каждый контур
        cyst_info = []
        total_area = 0
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            # Находим центр масс
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = 0, 0
            
            # Вычисляем эквивалентный диаметр
            equivalent_diameter = np.sqrt(4 * area / np.pi)
            
            cyst_info.append({
                "id": i + 1,
                "area_pixels": area,
                "area_mm2": area * 0.1,  # Примерное преобразование в мм²
                "perimeter_pixels": perimeter,
                "perimeter_mm": perimeter * 0.1,
                "center": (cx, cy),
                "equivalent_diameter_pixels": equivalent_diameter,
                "equivalent_diameter_mm": equivalent_diameter * 0.1
            })
            
            total_area += area
        
        return {
            "total_cysts": len(contours),
            "total_area_pixels": total_area,
            "total_area_mm2": total_area * 0.1,
            "cysts": cyst_info
        }
        
    except Exception as e:
        return {"error": f"Ошибка при анализе: {str(e)}"}


def calculate_root_cyst_overlap(tooth_masks_dir: str, 
                               cyst_mask_path: str, 
                               output_path: str = None) -> dict:
    """
    Рассчитывает процент поражения корня каждого зуба кистой
    
    Args:
        tooth_masks_dir (str): Путь к директории с масками зубов
        cyst_mask_path (str): Путь к маске кисты
        output_path (str): Путь для сохранения результатов (опционально)
    
    Returns:
        dict: Словарь с информацией о поражении каждого зуба
    """
    try:
        # Загружаем маску кисты
        cyst_mask = cv2.imread(cyst_mask_path, cv2.IMREAD_GRAYSCALE)
        if cyst_mask is None:
            return {"error": "Не удалось загрузить маску кисты"}
        
        # Получаем список масок зубов
        tooth_mask_files = [f for f in os.listdir(tooth_masks_dir) 
                           if f.startswith('tooth_') and f.endswith('.png')]
        
        if not tooth_mask_files:
            return {"error": "Не найдены маски зубов в указанной директории"}
        
        results = {
            "cyst_mask_path": cyst_mask_path,
            "tooth_masks_dir": tooth_masks_dir,
            "total_teeth": len(tooth_mask_files),
            "affected_teeth": 0,
            "teeth_analysis": []
        }
        
        total_overlap_area = 0
        
        # Анализируем каждый зуб
        for tooth_file in sorted(tooth_mask_files):
            tooth_path = os.path.join(tooth_masks_dir, tooth_file)
            tooth_mask = cv2.imread(tooth_path, cv2.IMREAD_GRAYSCALE)
            
            if tooth_mask is None:
                continue
            
            # Извлекаем номер зуба и FDI из имени файла
            tooth_name = tooth_file.replace('.png', '')
            parts = tooth_name.split('_')
            tooth_number = parts[1] if len(parts) > 1 else "unknown"
            fdi_number = parts[3] if len(parts) > 3 else "unknown"
            
            # Находим пересечение маски зуба с маской кисты
            overlap_mask = cv2.bitwise_and(tooth_mask, cyst_mask)
            overlap_area = cv2.countNonZero(overlap_mask)
            
            # Вычисляем площадь зуба
            tooth_area = cv2.countNonZero(tooth_mask)
            
            # Вычисляем процент поражения
            overlap_percentage = (overlap_area / tooth_area * 100) if tooth_area > 0 else 0
            
            # Определяем длину корня (приблизительно как высота зуба)
            tooth_contours, _ = cv2.findContours(tooth_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            root_length = 0
            if tooth_contours:
                # Находим самый большой контур
                largest_contour = max(tooth_contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                root_length = h  # Высота как приблизительная длина корня
            
            # Анализируем поражение корня
            root_overlap = _analyze_root_overlap(tooth_mask, cyst_mask, root_length)
            
            tooth_analysis = {
                "tooth_file": tooth_file,
                "tooth_number": tooth_number,
                "fdi_number": fdi_number,
                "total_area_pixels": tooth_area,
                "overlap_area_pixels": overlap_area,
                "overlap_percentage": round(overlap_percentage, 2),
                "root_length_pixels": root_length,
                "root_overlap_percentage": root_overlap["percentage"],
                "root_overlap_length": root_overlap["length"],
                "severity": _get_severity_level(overlap_percentage),
                "is_affected": overlap_area > 0
            }
            
            results["teeth_analysis"].append(tooth_analysis)
            
            if overlap_area > 0:
                results["affected_teeth"] += 1
                total_overlap_area += overlap_area
        
        # Добавляем общую статистику
        results["total_overlap_area"] = total_overlap_area
        results["average_overlap_percentage"] = round(
            sum(t["overlap_percentage"] for t in results["teeth_analysis"]) / len(results["teeth_analysis"]), 2
        ) if results["teeth_analysis"] else 0
        
        # Сохраняем результаты если указан путь
        if output_path:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Результаты анализа сохранены в: {output_path}")
        
        return results
        
    except Exception as e:
        return {"error": f"Ошибка при анализе поражения корней: {str(e)}"}


def _analyze_root_overlap(tooth_mask: np.ndarray, 
                         cyst_mask: np.ndarray, 
                         root_length: int) -> dict:
    """
    Анализирует поражение корня зуба кистой
    """
    try:
        # Находим контуры зуба
        tooth_contours, _ = cv2.findContours(tooth_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not tooth_contours:
            return {"percentage": 0, "length": 0}
        
        # Находим самый большой контур зуба
        largest_contour = max(tooth_contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Создаём маску корня (нижняя часть зуба)
        root_mask = np.zeros_like(tooth_mask)
        root_height = int(h * 0.6)  # Корень составляет примерно 60% высоты зуба
        root_y_start = y + h - root_height
        
        # Заполняем область корня
        cv2.rectangle(root_mask, (x, root_y_start), (x + w, y + h), 255, -1)
        
        # Находим пересечение корня с кистой
        root_cyst_overlap = cv2.bitwise_and(root_mask, cyst_mask)
        root_overlap_area = cv2.countNonZero(root_cyst_overlap)
        root_area = cv2.countNonZero(root_mask)
        
        # Вычисляем процент поражения корня
        root_overlap_percentage = (root_overlap_area / root_area * 100) if root_area > 0 else 0
        
        return {
            "percentage": round(root_overlap_percentage, 2),
            "length": root_overlap_area
        }
        
    except Exception as e:
        return {"percentage": 0, "length": 0}


def _get_severity_level(overlap_percentage: float) -> str:
    """
    Определяет уровень тяжести поражения
    """
    if overlap_percentage == 0:
        return "Нет поражения"
    elif overlap_percentage < 10:
        return "Лёгкое"
    elif overlap_percentage < 30:
        return "Умеренное"
    elif overlap_percentage < 50:
        return "Тяжёлое"
    else:
        return "Критическое"


def visualize_root_cyst_overlap(tooth_masks_dir: str, 
                               cyst_mask_path: str, 
                               original_image_path: str,
                               output_path: str) -> bool:
    """
    Визуализирует поражение корней зубов кистой
    
    Args:
        tooth_masks_dir (str): Путь к директории с масками зубов
        cyst_mask_path (str): Путь к маске кисты
        original_image_path (str): Путь к исходному изображению
        output_path (str): Путь для сохранения визуализации
    
    Returns:
        bool: True если операция выполнена успешно
    """
    try:
        # Загружаем изображения
        original_image = cv2.imread(original_image_path)
        cyst_mask = cv2.imread(cyst_mask_path, cv2.IMREAD_GRAYSCALE)
        
        if original_image is None or cyst_mask is None:
            print("Ошибка: Не удалось загрузить изображения")
            return False
        
        # Создаём визуализацию
        visualization = original_image.copy()
        
        # Получаем список масок зубов
        tooth_mask_files = [f for f in os.listdir(tooth_masks_dir) 
                           if f.startswith('tooth_') and f.endswith('.png')]
        
        # Цвета для разных уровней поражения
        colors = {
            "Нет поражения": (0, 255, 0),      # Зелёный
            "Лёгкое": (255, 255, 0),           # Жёлтый
            "Умеренное": (255, 165, 0),        # Оранжевый
            "Тяжёлое": (255, 0, 0),            # Красный
            "Критическое": (128, 0, 128)       # Фиолетовый
        }
        
        # Анализируем каждый зуб
        for tooth_file in sorted(tooth_mask_files):
            tooth_path = os.path.join(tooth_masks_dir, tooth_file)
            tooth_mask = cv2.imread(tooth_path, cv2.IMREAD_GRAYSCALE)
            
            if tooth_mask is None:
                continue
            
            # Находим пересечение
            overlap_mask = cv2.bitwise_and(tooth_mask, cyst_mask)
            overlap_area = cv2.countNonZero(overlap_mask)
            tooth_area = cv2.countNonZero(tooth_mask)
            overlap_percentage = (overlap_area / tooth_area * 100) if tooth_area > 0 else 0
            
            # Определяем уровень поражения
            severity = _get_severity_level(overlap_percentage)
            color = colors.get(severity, (255, 255, 255))
            
            # Находим контуры зуба для отображения
            tooth_contours, _ = cv2.findContours(tooth_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if tooth_contours:
                # Рисуем контур зуба
                cv2.drawContours(visualization, tooth_contours, -1, color, 2)
                
                # Добавляем текст с процентом поражения
                largest_contour = max(tooth_contours, key=cv2.contourArea)
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Извлекаем номер зуба
                    tooth_name = tooth_file.replace('.png', '')
                    parts = tooth_name.split('_')
                    fdi_number = parts[3] if len(parts) > 3 else "?"
                    
                    # Добавляем текст
                    text = f"FDI:{fdi_number} {overlap_percentage:.1f}%"
                    cv2.putText(visualization, text, (cx-20, cy), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Сохраняем результат
        cv2.imwrite(output_path, visualization)
        print(f"Визуализация сохранена в: {output_path}")
        return True
        
    except Exception as e:
        print(f"Ошибка при создании визуализации: {str(e)}")
        return False


if __name__ == "__main__":
    # Пример использования
    print("Модуль для анализа стоматологических изображений")
    print("Доступные функции:")
    print("1. replace_cyst_volume() - замена объёма кисты")
    print("2. analyze_cyst_volume() - анализ объёма кисты")
    print("3. calculate_root_cyst_overlap() - анализ поражения корней кистой")
    print("4. visualize_root_cyst_overlap() - визуализация поражения корней")
