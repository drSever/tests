# Инференс тестовой модели YOLOv8 на ортопантомограммах

## Структура репозитория
- `/model`  - каталог с обученными моделями    
    - *model_tooth_segmentation.pt* - обученная модель для сегментации зубов [скачать](https://drive.google.com/file/d/1EoKvjJbp14VcDO2dMKeoHm3slB65UFsA/view?usp=share_link)
    - *model_rc_segmentation.pt*  - обученная модель для сегментации кист [скачать](https://drive.google.com/file/d/17NXUvA-Svh88xoS_ehfPACLQQM5VKLPn/view?usp=share_link)
- `/image_test_rc`  - пример каталога с сохраненными масками кист для изображения *image_test*
- `/image_test_ts`  - пример каталога с сохраненными масками зубов для изображения *image_test*
- *image_test.jpg* - пример ортопантомограммы
- *rc_segmentation*.py - скрипт для выполнения сегментации кист на ортопантомограмме
- *tooth_segmentation*.py - скрипт для выполнения сегментации зубов на ортопантомограмме
- *env.yml* - окружение Anaconda

## 1. Сегментация зубов
Для выполнении сегментации зубов на ортопантомограмме запустите в терминале скрипт *tooth_segmentation.py*:    

 `python tooth_segmentation.py --image <path_to_image> --model <path_to_model> --output <path_to_output_folder>`

 где:
 - `<path_to_image>`  - путь к ортопантомограмме
 - `<path_to_model>`  - путь к модели сегментации зубов (по умолчанию *'model/model_tooth_segmentation.py'*)
 - `<path_to_output_folder>`  - путь к каталогу с результатами (масками), по умолчанию *'output'*

Для вызова помощи запустите в терминале:    
`python tooth_segmentation.py --help`

**Пример использования**:    
`python tooth_segmentation.py --image image_test.png --output image_test_ts`    
где,  
- `image_test.jpg` - файл ортопантомограммы
- `image_test_ts` - каталог с сохраненными масками

### Результат работы скрипта

В указанном каталоге будут сохранены маски сегментированных зубов в виде файлов изображений *.png*, где вторая (последняя) цифра будет указывать на номер зуба по классификации FDI-ISO.    
Кроме того будут сохранены следующие файлы:
- *all_masks_combined.png* - все маски собраны на одном изображении
- *annotated_image.jpg* - аннотированное исходное изображение
- *image_yolo.txt* - файл аннотаций в формате YOLO вида `class_id x1 y1 x2 y2 x3 y3 ...`

## 2. Сегментация кист

Для выполнении сегментации кист на ортопантомограмме запустите в терминале скрипт *rc_segmentation.py*:    

 `python rc_segmentation.py --image <path_to_image> --model <path_to_model> --output <path_to_output_folder>`

 где:
 - `<path_to_image>`  - путь к ортопантомограмме
 - `<path_to_model>`  - путь к модели сегментации кист (по умолчанию *'model/model_rc_segmentation.py'*)
 - `<path_to_output_folder>`  - путь к каталогу с результатами (масками), по умолчанию *'output'*

Для вызова помощи запустите в терминале:    
`python rc_segmentation.py --help`

**Пример использования**:    
`python rc_segmentation.py --input image_test.png --output image_test_rc`    
где,  
- `image_test.jpg` - файл ортопантомограммы
- `image_test_rc` - каталог с сохраненными масками

### Результат работы скрипта

В указанном каталоге будут сохранены следующие файлы:    
- *<имя файла изображения>_mask.png* - маски кист
- *<имя файла изображения>_masked.png* - исходное изображение с наложенной маской
- *<имя файла изображения>.txt* - файл аннотаций в формате YOLO вида `class_id x1 y1 x2 y2 x3 y3 ...`