#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI приложение для анализа стоматологических изображений
"""

import os
import shutil
import uuid
import sys
from pathlib import Path
from typing import List, Optional
import json
import time

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from dental_analysis import (
    replace_cyst_volume, 
    analyze_cyst_volume, 
    calculate_root_cyst_overlap, 
    visualize_root_cyst_overlap
)


# Создаём FastAPI приложение
app = FastAPI(
    title="Dental Analysis API",
    description="API для анализа стоматологических изображений",
    version="1.0.0"
)

# Создаём необходимые директории
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
STATIC_RESULTS_DIR = Path("static/results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
STATIC_RESULTS_DIR.mkdir(exist_ok=True)

# Настройка статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Модели данных
class AnalysisResult(BaseModel):
    task_id: str
    status: str
    message: str
    results: Optional[dict] = None
    error: Optional[str] = None

class AnalysisRequest(BaseModel):
    image_path: str
    analyze_teeth: bool = True
    analyze_cysts: bool = True
    replace_cyst_volume: bool = False
    replacement_method: str = "interpolation"

# Глобальное хранилище результатов анализа
analysis_results = {}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload", response_class=JSONResponse)
async def upload_image(file: UploadFile = File(...)):
    """Загрузка изображения"""
    try:
        # Проверяем тип файла
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        # Создаём уникальное имя файла
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / filename
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "message": "Изображение успешно загружено"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")

@app.post("/analyze", response_class=JSONResponse)
async def analyze_image(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    analyze_teeth: bool = Form(True),
    analyze_cysts: bool = Form(True),
    should_replace_cyst_volume: bool = Form(False),
    replacement_method: str = Form("interpolation")
):
    """Запуск анализа изображения"""
    try:
        # Проверяем существование файла
        image_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        if not image_files:
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        image_path = str(image_files[0])
        task_id = str(uuid.uuid4())
        
        # Инициализируем результат
        analysis_results[task_id] = {
            "status": "processing",
            "message": "Анализ начат",
            "results": None,
            "error": None
        }
        
        # Запускаем анализ в фоновом режиме
        background_tasks.add_task(
            perform_analysis,
            task_id,
            image_path,
            analyze_teeth,
            analyze_cysts,
            should_replace_cyst_volume,
            replacement_method
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Анализ запущен"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка запуска анализа: {str(e)}")

@app.get("/status/{task_id}", response_class=JSONResponse)
async def get_analysis_status(task_id: str):
    """Получение статуса анализа"""
    if task_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return analysis_results[task_id]

@app.get("/results/{task_id}", response_class=JSONResponse)
async def get_analysis_results(task_id: str):
    """Получение результатов анализа"""
    if task_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    result = analysis_results[task_id]
    if result["status"] != "completed":
        raise HTTPException(status_code=400, detail="Анализ ещё не завершён")
    
    return result

async def perform_analysis(
    task_id: str,
    image_path: str,
    analyze_teeth: bool,
    analyze_cysts: bool,
    should_replace_cyst_volume: bool,
    replacement_method: str
):
    """Выполнение анализа в фоновом режиме"""
    try:
        analysis_results[task_id]["status"] = "processing"
        analysis_results[task_id]["message"] = "Выполняется сегментация..."
        
        results = {
            "image_path": image_path,
            "analysis_time": time.time(),
            "teeth_analysis": None,
            "cyst_analysis": None,
            "root_overlap_analysis": None,
            "visualizations": []
        }
        
        # Создаём директории для результатов
        task_dir = RESULTS_DIR / task_id
        task_dir.mkdir(exist_ok=True)
        
        # Анализ зубов
        if analyze_teeth:
            analysis_results[task_id]["message"] = "Анализ зубов..."
            teeth_output_dir = task_dir / "teeth"
            teeth_output_dir.mkdir(exist_ok=True)
            
            # Запускаем сегментацию зубов
            try:
                # Импортируем модуль здесь для избежания проблем с импортом
                import tooth_segmentation
                
                # Создаём аргументы для main функции
                sys.argv = [
                    "tooth_segmentation.py",
                    "--image", image_path,
                    "--output", str(teeth_output_dir)
                ]
                
                # Запускаем сегментацию
                tooth_segmentation.main()
                
                results["teeth_analysis"] = {
                    "output_dir": str(teeth_output_dir),
                    "masks_count": len(list(teeth_output_dir.glob("tooth_*.png")))
                }
            except Exception as e:
                print(f"Ошибка сегментации зубов: {e}")
                results["teeth_analysis"] = {"error": str(e)}
        
        # Анализ кист
        if analyze_cysts:
            analysis_results[task_id]["message"] = "Анализ кист..."
            cyst_output_dir = task_dir / "cysts"
            cyst_output_dir.mkdir(exist_ok=True)
            
            try:
                # Импортируем модуль здесь
                import rc_segmentation
                
                # Создаём аргументы для main функции
                sys.argv = [
                    "rc_segmentation.py",
                    "--input", image_path,
                    "--output", str(cyst_output_dir)
                ]
                
                # Запускаем сегментацию
                rc_segmentation.main()
                
                # Анализируем объём кисты
                cyst_mask_path = cyst_output_dir / f"{Path(image_path).stem}_mask.png"
                if cyst_mask_path.exists():
                    cyst_analysis = analyze_cyst_volume(str(cyst_mask_path))
                    results["cyst_analysis"] = cyst_analysis
                    
                    # Замена объёма кисты если требуется
                    if should_replace_cyst_volume and "error" not in cyst_analysis:
                        analysis_results[task_id]["message"] = "Замена объёма кисты..."
                        replaced_path = cyst_output_dir / f"cyst_replaced_{replacement_method}.png"
                        replace_cyst_volume(
                            image_path,
                            str(cyst_mask_path),
                            str(replaced_path),
                            replacement_method
                        )
                        results["visualizations"].append(str(replaced_path))
                else:
                    results["cyst_analysis"] = {"error": "Маска кисты не найдена"}
            except Exception as e:
                print(f"Ошибка сегментации кист: {e}")
                results["cyst_analysis"] = {"error": str(e)}
        
        # Анализ поражения корней
        if analyze_teeth and analyze_cysts:
            analysis_results[task_id]["message"] = "Анализ поражения корней..."
            
            teeth_dir = task_dir / "teeth"
            cyst_mask_path = task_dir / "cysts" / f"{Path(image_path).stem}_mask.png"
            
            if teeth_dir.exists() and cyst_mask_path.exists():
                try:
                    # Анализ поражения корней
                    root_analysis = calculate_root_cyst_overlap(
                        str(teeth_dir),
                        str(cyst_mask_path)
                    )
                    results["root_overlap_analysis"] = root_analysis
                    
                    # Создание визуализации
                    visualization_path = task_dir / "root_cyst_visualization.png"
                    visualize_root_cyst_overlap(
                        str(teeth_dir),
                        str(cyst_mask_path),
                        image_path,
                        str(visualization_path)
                    )
                    results["visualizations"].append(str(visualization_path))
                except Exception as e:
                    print(f"Ошибка анализа поражения корней: {e}")
                    results["root_overlap_analysis"] = {"error": str(e)}
        
        # Копируем результаты в статическую директорию для веб-доступа
        static_task_dir = STATIC_RESULTS_DIR / task_id
        if static_task_dir.exists():
            shutil.rmtree(static_task_dir)
        shutil.copytree(task_dir, static_task_dir)
        
        # Обновляем пути к визуализациям для веб-доступа
        web_visualizations = []
        for viz_path in results["visualizations"]:
            filename = Path(viz_path).name
            web_visualizations.append(f"results/{task_id}/{filename}")
        results["visualizations"] = web_visualizations
        
        # Обновляем результаты
        analysis_results[task_id]["status"] = "completed"
        analysis_results[task_id]["message"] = "Анализ завершён"
        analysis_results[task_id]["results"] = results
        
    except Exception as e:
        analysis_results[task_id]["status"] = "error"
        analysis_results[task_id]["error"] = str(e)
        analysis_results[task_id]["message"] = f"Ошибка анализа: {str(e)}"

@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_tasks": len([r for r in analysis_results.values() if r["status"] == "processing"])
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
