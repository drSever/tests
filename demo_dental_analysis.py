#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрационный скрипт для модуля dental_analysis
Показывает использование всех функций
"""

import os
import json
from dental_analysis import replace_cyst_volume, analyze_cyst_volume, calculate_root_cyst_overlap, visualize_root_cyst_overlap


def main():
    print("🦷 Демонстрация функций анализа стоматологических изображений")
    print("=" * 60)
    
    # Пути к файлам
    image_path = "image_test.png"
    mask_path = "test_output_rc/image_test_mask.png"
    tooth_masks_dir = "test_output_teeth"
    
    # Проверяем наличие файлов
    if not os.path.exists(image_path):
        print(f"❌ Ошибка: Файл {image_path} не найден")
        return
    
    if not os.path.exists(mask_path):
        print(f"❌ Ошибка: Файл {mask_path} не найден")
        return
    
    if not os.path.exists(tooth_masks_dir):
        print(f"❌ Ошибка: Директория {tooth_masks_dir} не найдена")
        return
    
    print(f"✅ Найдены файлы:")
    print(f"   Изображение: {image_path}")
    print(f"   Маска кисты: {mask_path}")
    print(f"   Маски зубов: {tooth_masks_dir}")
    print()
    
    # 1. Анализ объёма кисты
    print("📊 1. Анализ объёма кисты")
    print("-" * 30)
    
    cyst_analysis = analyze_cyst_volume(mask_path)
    
    if "error" in cyst_analysis:
        print(f"❌ Ошибка анализа: {cyst_analysis['error']}")
    else:
        print(f"📈 Найдено кист: {cyst_analysis['total_cysts']}")
        print(f"📏 Общая площадь: {cyst_analysis['total_area_pixels']:.1f} пикселей ({cyst_analysis['total_area_mm2']:.1f} мм²)")
        
        for cyst in cyst_analysis['cysts']:
            print(f"   🦷 Киста #{cyst['id']}:")
            print(f"      Площадь: {cyst['area_pixels']:.1f} пикселей ({cyst['area_mm2']:.1f} мм²)")
            print(f"      Периметр: {cyst['perimeter_pixels']:.1f} пикселей ({cyst['perimeter_mm']:.1f} мм)")
            print(f"      Диаметр: {cyst['equivalent_diameter_pixels']:.1f} пикселей ({cyst['equivalent_diameter_mm']:.1f} мм)")
            print(f"      Центр: {cyst['center']}")
    
    print()
    
    # 2. Замена объёма кисты разными методами
    print("🔧 2. Замена объёма кисты")
    print("-" * 30)
    
    methods = [
        ("interpolation", "Интерполяция", "cyst_replaced_interpolation.png"),
        ("blur", "Размытие", "cyst_replaced_blur.png"),
        ("color_fill", "Заполнение цветом", "cyst_replaced_color.png")
    ]
    
    for method, method_name, output_file in methods:
        output_path = f"test_output_rc/{output_file}"
        
        print(f"🔄 Метод: {method_name}")
        
        if method == "color_fill":
            success = replace_cyst_volume(image_path, mask_path, output_path, method, (200, 200, 200))
        else:
            success = replace_cyst_volume(image_path, mask_path, output_path, method)
        
        if success:
            print(f"   ✅ Успешно! Результат: {output_path}")
        else:
            print(f"   ❌ Ошибка при обработке")
        
        print()
    
    # 3. Анализ поражения корней зубов кистой
    print("🦷 3. Анализ поражения корней зубов кистой")
    print("-" * 45)
    
    root_analysis = calculate_root_cyst_overlap(tooth_masks_dir, mask_path)
    
    if "error" in root_analysis:
        print(f"❌ Ошибка анализа: {root_analysis['error']}")
    else:
        print(f"📈 Общая статистика:")
        print(f"   Всего зубов: {root_analysis['total_teeth']}")
        print(f"   Поражённых зубов: {root_analysis['affected_teeth']}")
        print(f"   Средний процент поражения: {root_analysis['average_overlap_percentage']}%")
        
        # Показываем поражённые зубы
        affected_teeth = [t for t in root_analysis['teeth_analysis'] if t['is_affected']]
        if affected_teeth:
            print(f"   🦷 Поражённые зубы:")
            for tooth in affected_teeth:
                print(f"      FDI {tooth['fdi_number']}: {tooth['overlap_percentage']}% ({tooth['severity']})")
        else:
            print(f"   ✅ Поражённых зубов не обнаружено")
    
    print()
    
    # 4. Создание визуализации поражения корней
    print("🎨 4. Создание визуализации поражения корней")
    print("-" * 45)
    
    visualization_path = "test_output_rc/root_cyst_visualization.png"
    success = visualize_root_cyst_overlap(
        tooth_masks_dir, 
        mask_path, 
        image_path, 
        visualization_path
    )
    
    if success:
        print(f"✅ Визуализация создана: {visualization_path}")
    else:
        print("❌ Ошибка при создании визуализации")
    
    print()
    
    # 5. Сохранение результатов анализа
    print("💾 5. Сохранение результатов")
    print("-" * 30)
    
    # Сохраняем анализ кисты
    cyst_analysis_file = "test_output_rc/cyst_analysis.json"
    with open(cyst_analysis_file, 'w', encoding='utf-8') as f:
        json.dump(cyst_analysis, f, indent=2, ensure_ascii=False)
    
    # Сохраняем анализ поражения корней
    root_analysis_file = "test_output_rc/root_cyst_analysis.json"
    with open(root_analysis_file, 'w', encoding='utf-8') as f:
        json.dump(root_analysis, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Результаты анализа кисты сохранены в: {cyst_analysis_file}")
    print(f"📄 Результаты анализа поражения корней сохранены в: {root_analysis_file}")
    
    print()
    print("🎉 Демонстрация завершена!")
    print("📁 Результаты сохранены в папке test_output_rc/")
    print()
    print("📋 Доступные функции:")
    print("   1. replace_cyst_volume() - замена объёма кисты")
    print("   2. analyze_cyst_volume() - анализ объёма кисты")
    print("   3. calculate_root_cyst_overlap() - анализ поражения корней кистой")
    print("   4. visualize_root_cyst_overlap() - визуализация поражения корней")


if __name__ == "__main__":
    main()
