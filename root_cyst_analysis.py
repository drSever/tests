#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для анализа поражения корней зубов кистой
Рассчитывает процент поражения каждого зуба и создаёт визуализацию
"""

import os
import json
from dental_analysis import calculate_root_cyst_overlap, visualize_root_cyst_overlap


def main():
    print("🦷 Анализ поражения корней зубов кистой")
    print("=" * 50)
    
    # Пути к файлам
    tooth_masks_dir = "test_output_teeth"
    cyst_mask_path = "test_output_rc/image_test_mask.png"
    original_image_path = "image_test.png"
    
    # Проверяем наличие файлов
    if not os.path.exists(tooth_masks_dir):
        print(f"❌ Ошибка: Директория {tooth_masks_dir} не найдена")
        return
    
    if not os.path.exists(cyst_mask_path):
        print(f"❌ Ошибка: Файл {cyst_mask_path} не найден")
        return
    
    if not os.path.exists(original_image_path):
        print(f"❌ Ошибка: Файл {original_image_path} не найден")
        return
    
    print(f"✅ Найдены файлы:")
    print(f"   Маски зубов: {tooth_masks_dir}")
    print(f"   Маска кисты: {cyst_mask_path}")
    print(f"   Исходное изображение: {original_image_path}")
    print()
    
    # 1. Анализ поражения корней
    print("📊 1. Анализ поражения корней зубов кистой")
    print("-" * 45)
    
    output_json = "test_output_rc/root_cyst_analysis.json"
    analysis_result = calculate_root_cyst_overlap(
        tooth_masks_dir, 
        cyst_mask_path, 
        output_json
    )
    
    if "error" in analysis_result:
        print(f"❌ Ошибка анализа: {analysis_result['error']}")
        return
    
    # Выводим общую статистику
    print(f"📈 Общая статистика:")
    print(f"   Всего зубов: {analysis_result['total_teeth']}")
    print(f"   Поражённых зубов: {analysis_result['affected_teeth']}")
    print(f"   Средний процент поражения: {analysis_result['average_overlap_percentage']}%")
    print()
    
    # Выводим детальную информацию по поражённым зубам
    affected_teeth = [t for t in analysis_result['teeth_analysis'] if t['is_affected']]
    
    if affected_teeth:
        print("🦷 Поражённые зубы:")
        print("-" * 30)
        
        for tooth in affected_teeth:
            print(f"   Зуб FDI {tooth['fdi_number']}:")
            print(f"      Общее поражение: {tooth['overlap_percentage']}%")
            print(f"      Поражение корня: {tooth['root_overlap_percentage']}%")
            print(f"      Тяжесть: {tooth['severity']}")
            print()
    else:
        print("✅ Поражённых зубов не обнаружено")
        print()
    
    # 2. Создание визуализации
    print("🎨 2. Создание визуализации поражения")
    print("-" * 35)
    
    output_visualization = "test_output_rc/root_cyst_visualization.png"
    success = visualize_root_cyst_overlap(
        tooth_masks_dir,
        cyst_mask_path,
        original_image_path,
        output_visualization
    )
    
    if success:
        print(f"✅ Визуализация создана: {output_visualization}")
    else:
        print("❌ Ошибка при создании визуализации")
    
    print()
    
    # 3. Создание отчёта
    print("📄 3. Создание подробного отчёта")
    print("-" * 30)
    
    report_path = "test_output_rc/root_cyst_report.txt"
    create_detailed_report(analysis_result, report_path)
    
    print(f"📄 Подробный отчёт сохранён в: {report_path}")
    
    print()
    print("🎉 Анализ завершён!")
    print("📁 Результаты сохранены в папке test_output_rc/")


def create_detailed_report(analysis_result: dict, report_path: str):
    """
    Создаёт подробный текстовый отчёт
    """
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("ОТЧЁТ О ПОРАЖЕНИИ КОРНЕЙ ЗУБОВ КИСТОЙ\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("ОБЩАЯ СТАТИСТИКА:\n")
        f.write("-" * 20 + "\n")
        f.write(f"Всего зубов: {analysis_result['total_teeth']}\n")
        f.write(f"Поражённых зубов: {analysis_result['affected_teeth']}\n")
        f.write(f"Средний процент поражения: {analysis_result['average_overlap_percentage']}%\n")
        f.write(f"Общая площадь поражения: {analysis_result['total_overlap_area']} пикселей\n\n")
        
        f.write("ДЕТАЛЬНЫЙ АНАЛИЗ ПО ЗУБАМ:\n")
        f.write("-" * 30 + "\n")
        
        # Сортируем зубы по проценту поражения
        sorted_teeth = sorted(
            analysis_result['teeth_analysis'], 
            key=lambda x: x['overlap_percentage'], 
            reverse=True
        )
        
        for tooth in sorted_teeth:
            f.write(f"Зуб FDI {tooth['fdi_number']}:\n")
            f.write(f"  Общее поражение: {tooth['overlap_percentage']}%\n")
            f.write(f"  Поражение корня: {tooth['root_overlap_percentage']}%\n")
            f.write(f"  Площадь зуба: {tooth['total_area_pixels']} пикселей\n")
            f.write(f"  Площадь поражения: {tooth['overlap_area_pixels']} пикселей\n")
            f.write(f"  Длина корня: {tooth['root_length_pixels']} пикселей\n")
            f.write(f"  Тяжесть поражения: {tooth['severity']}\n")
            f.write(f"  Статус: {'Поражён' if tooth['is_affected'] else 'Не поражён'}\n")
            f.write("\n")
        
        f.write("КЛАССИФИКАЦИЯ ТЯЖЕСТИ ПОРАЖЕНИЯ:\n")
        f.write("-" * 40 + "\n")
        f.write("0% - Нет поражения\n")
        f.write("1-9% - Лёгкое поражение\n")
        f.write("10-29% - Умеренное поражение\n")
        f.write("30-49% - Тяжёлое поражение\n")
        f.write("50%+ - Критическое поражение\n\n")
        
        f.write("РЕКОМЕНДАЦИИ:\n")
        f.write("-" * 15 + "\n")
        
        critical_teeth = [t for t in analysis_result['teeth_analysis'] 
                         if t['severity'] in ['Тяжёлое', 'Критическое']]
        
        if critical_teeth:
            f.write("⚠️  КРИТИЧЕСКИЕ СЛУЧАИ:\n")
            for tooth in critical_teeth:
                f.write(f"   - Зуб FDI {tooth['fdi_number']}: {tooth['overlap_percentage']}% поражения\n")
            f.write("   Рекомендуется немедленная консультация стоматолога!\n\n")
        
        affected_count = analysis_result['affected_teeth']
        if affected_count > 0:
            f.write(f"📋 ОБЩИЕ РЕКОМЕНДАЦИИ:\n")
            f.write(f"   - Поражено {affected_count} зубов из {analysis_result['total_teeth']}\n")
            f.write(f"   - Необходимо детальное обследование поражённых зубов\n")
            f.write(f"   - Рекомендуется рентгенологический контроль\n")
        else:
            f.write("✅ Поражений не обнаружено. Рекомендуется профилактический осмотр.\n")


if __name__ == "__main__":
    main()
