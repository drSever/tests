#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска FastAPI сервера
"""

import uvicorn
import os
import sys
from pathlib import Path

def main():
    # Проверяем наличие необходимых файлов
    required_files = [
        "app.py",
        "dental_analysis.py",
        "tooth_segmentation.py",
        "rc_segmentation.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Отсутствуют необходимые файлы:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nУбедитесь, что все файлы находятся в текущей директории.")
        return
    
    # Проверяем наличие моделей
    model_files = [
        "model/model_tooth_segmentation.pt",
        "model/model_rc_segmentation.pt"
    ]
    
    missing_models = []
    for model in model_files:
        if not Path(model).exists():
            missing_models.append(model)
    
    if missing_models:
        print("⚠️  Предупреждение: Отсутствуют модели:")
        for model in missing_models:
            print(f"   - {model}")
        print("\nМодели можно скачать по ссылкам в README.md")
    
    # Создаём необходимые директории
    directories = ["uploads", "results", "static/results", "templates", "static/css", "static/js"]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("🚀 Запуск Dental Analysis Web Application...")
    print("📁 Созданы необходимые директории")
    print("🌐 Сервер будет доступен по адресу: http://localhost:8000")
    print("📖 API документация: http://localhost:8000/docs")
    print("\nНажмите Ctrl+C для остановки сервера")
    
    # Запускаем сервер
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
