// Dental Analysis Web Application
class DentalAnalysisApp {
    constructor() {
        this.currentFileId = null;
        this.currentTaskId = null;
        this.statusCheckInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
    }

    setupEventListeners() {
        // File input change
        document.getElementById('fileInput').addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // Start analysis button
        document.getElementById('startAnalysis').addEventListener('click', () => {
            this.startAnalysis();
        });

        // Checkbox for cyst volume replacement
        document.getElementById('replaceCystVolume').addEventListener('change', (e) => {
            const methodSection = document.getElementById('replacementMethod');
            methodSection.style.display = e.target.checked ? 'block' : 'none';
        });

        // Upload area click
        document.getElementById('uploadArea').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
    }

    setupDragAndDrop() {
        const uploadArea = document.getElementById('uploadArea');

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
    }

    async handleFileSelect(file) {
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.showError('Пожалуйста, выберите изображение');
            return;
        }

        // Show loading
        this.showModal('Загрузка изображения...');

        try {
            // Upload file
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.currentFileId = result.file_id;
                this.displayFileInfo(file, result.filename);
                this.showOptionsSection();
                this.hideModal();
            } else {
                throw new Error(result.detail || 'Ошибка загрузки');
            }
        } catch (error) {
            this.hideModal();
            this.showError(`Ошибка загрузки: ${error.message}`);
        }
    }

    displayFileInfo(file, filename) {
        const fileInfo = document.getElementById('fileInfo');
        const imagePreview = document.getElementById('imagePreview');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');

        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
        };
        reader.readAsDataURL(file);

        // Set file details
        fileName.textContent = filename;
        fileSize.textContent = this.formatFileSize(file.size);

        // Show file info
        fileInfo.style.display = 'flex';
        fileInfo.classList.add('fade-in');
    }

    showOptionsSection() {
        document.getElementById('optionsSection').style.display = 'block';
        document.getElementById('optionsSection').classList.add('fade-in');
    }

    async startAnalysis() {
        if (!this.currentFileId) {
            this.showError('Сначала загрузите изображение');
            return;
        }

        // Get analysis options
        const analyzeTeeth = document.getElementById('analyzeTeeth').checked;
        const analyzeCysts = document.getElementById('analyzeCysts').checked;
        const replaceCystVolume = document.getElementById('replaceCystVolume').checked;
        const replacementMethod = document.getElementById('methodSelect').value;

        if (!analyzeTeeth && !analyzeCysts) {
            this.showError('Выберите хотя бы один тип анализа');
            return;
        }

        // Show progress section
        this.showProgressSection();

        try {
            // Start analysis
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    file_id: this.currentFileId,
                    analyze_teeth: analyzeTeeth,
                    analyze_cysts: analyzeCysts,
                    replace_cyst_volume: replaceCystVolume,
                    replacement_method: replacementMethod
                })
            });

            const result = await response.json();

            if (result.success) {
                this.currentTaskId = result.task_id;
                this.startStatusChecking();
            } else {
                throw new Error(result.detail || 'Ошибка запуска анализа');
            }
        } catch (error) {
            this.showError(`Ошибка запуска анализа: ${error.message}`);
            this.hideProgressSection();
        }
    }

    startStatusChecking() {
        this.statusCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(`/status/${this.currentTaskId}`);
                const status = await response.json();

                this.updateProgress(status);

                if (status.status === 'completed') {
                    this.handleAnalysisComplete(status);
                } else if (status.status === 'error') {
                    this.handleAnalysisError(status);
                }
            } catch (error) {
                console.error('Error checking status:', error);
            }
        }, 2000);
    }

    updateProgress(status) {
        const progressStatus = document.getElementById('progressStatus');
        const progressFill = document.getElementById('progressFill');

        progressStatus.textContent = status.message;

        // Update progress bar based on status
        let progress = 0;
        if (status.message.includes('зубов')) progress = 25;
        else if (status.message.includes('кист')) progress = 50;
        else if (status.message.includes('корней')) progress = 75;
        else if (status.message.includes('завершён')) progress = 100;

        progressFill.style.width = `${progress}%`;

        // Update steps
        this.updateSteps(progress);
    }

    updateSteps(progress) {
        const steps = document.querySelectorAll('.step');
        steps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (progress >= (index + 1) * 25) {
                step.classList.add('completed');
            } else if (progress >= index * 25) {
                step.classList.add('active');
            }
        });
    }

    async handleAnalysisComplete(status) {
        clearInterval(this.statusCheckInterval);
        
        try {
            // Get detailed results
            const response = await fetch(`/results/${this.currentTaskId}`);
            const results = await response.json();

            this.displayResults(results);
            this.hideProgressSection();
            this.showResultsSection();
        } catch (error) {
            this.showError(`Ошибка получения результатов: ${error.message}`);
        }
    }

    handleAnalysisError(status) {
        clearInterval(this.statusCheckInterval);
        this.hideProgressSection();
        this.showError(`Ошибка анализа: ${status.error}`);
    }

    displayResults(results) {
        const data = results.results;

        // Display teeth analysis
        if (data.teeth_analysis) {
            this.displayTeethResults(data.teeth_analysis);
        }

        // Display cyst analysis
        if (data.cyst_analysis) {
            this.displayCystResults(data.cyst_analysis);
        }

        // Display root overlap analysis
        if (data.root_overlap_analysis) {
            this.displayRootResults(data.root_overlap_analysis);
        }

        // Display visualizations
        if (data.visualizations && data.visualizations.length > 0) {
            this.displayVisualizations(data.visualizations);
        }
    }

    displayTeethResults(teethData) {
        const content = document.getElementById('teethContent');
        content.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">Найдено зубов:</span>
                <span class="stat-value highlight">${teethData.masks_count}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Статус:</span>
                <span class="stat-value">✅ Завершён</span>
            </div>
        `;
    }

    displayCystResults(cystData) {
        const content = document.getElementById('cystContent');
        
        if (cystData.error) {
            content.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">Статус:</span>
                    <span class="stat-value">❌ Ошибка</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Ошибка:</span>
                    <span class="stat-value">${cystData.error}</span>
                </div>
            `;
        } else {
            content.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">Найдено кист:</span>
                    <span class="stat-value highlight">${cystData.total_cysts}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Общая площадь:</span>
                    <span class="stat-value">${cystData.total_area_pixels} пикселей</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Площадь (мм²):</span>
                    <span class="stat-value">${cystData.total_area_mm2.toFixed(1)} мм²</span>
                </div>
            `;
        }
    }

    displayRootResults(rootData) {
        const content = document.getElementById('rootContent');
        
        if (rootData.error) {
            content.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">Статус:</span>
                    <span class="stat-value">❌ Ошибка</span>
                </div>
            `;
        } else {
            const affectedTeeth = rootData.affected_teeth;
            const totalTeeth = rootData.total_teeth;
            
            content.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">Всего зубов:</span>
                    <span class="stat-value">${totalTeeth}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Поражённых зубов:</span>
                    <span class="stat-value highlight">${affectedTeeth}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Средний % поражения:</span>
                    <span class="stat-value">${rootData.average_overlap_percentage}%</span>
                </div>
            `;
        }
    }

    displayVisualizations(visualizations) {
        const grid = document.getElementById('visualizationsGrid');
        grid.innerHTML = '';

        visualizations.forEach((path, index) => {
            const item = document.createElement('div');
            item.className = 'visualization-item fade-in';
            
            const filename = path.split('/').pop();
            const caption = this.getVisualizationCaption(filename);
            
            item.innerHTML = `
                <img src="/static/results/${this.currentTaskId}/${filename}" alt="${caption}">
                <div class="caption">${caption}</div>
            `;
            
            grid.appendChild(item);
        });
    }

    getVisualizationCaption(filename) {
        if (filename.includes('root_cyst_visualization')) {
            return 'Поражение корней кистой';
        } else if (filename.includes('cyst_replaced_interpolation')) {
            return 'Киста заменена интерполяцией';
        } else if (filename.includes('cyst_replaced_blur')) {
            return 'Киста заменена размытием';
        } else if (filename.includes('cyst_replaced_color')) {
            return 'Киста заменена цветом';
        }
        return 'Визуализация';
    }

    showProgressSection() {
        document.getElementById('progressSection').style.display = 'block';
        document.getElementById('progressSection').classList.add('fade-in');
    }

    hideProgressSection() {
        document.getElementById('progressSection').style.display = 'none';
    }

    showResultsSection() {
        document.getElementById('resultsSection').style.display = 'block';
        document.getElementById('resultsSection').classList.add('fade-in');
    }

    showModal(message) {
        const modal = document.getElementById('loadingModal');
        const modalMessage = document.getElementById('modalMessage');
        modalMessage.textContent = message;
        modal.classList.add('show');
    }

    hideModal() {
        const modal = document.getElementById('loadingModal');
        modal.classList.remove('show');
    }

    showError(message) {
        // Simple error display - you can enhance this with a proper toast notification
        alert(message);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    resetAnalysis() {
        // Reset all sections
        document.getElementById('uploadSection').style.display = 'block';
        document.getElementById('optionsSection').style.display = 'none';
        document.getElementById('progressSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('fileInfo').style.display = 'none';

        // Reset form
        document.getElementById('fileInput').value = '';
        document.getElementById('analyzeTeeth').checked = true;
        document.getElementById('analyzeCysts').checked = true;
        document.getElementById('replaceCystVolume').checked = false;
        document.getElementById('replacementMethod').style.display = 'none';

        // Clear intervals
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }

        // Reset variables
        this.currentFileId = null;
        this.currentTaskId = null;
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dentalApp = new DentalAnalysisApp();
});

// Global function for reset
function resetAnalysis() {
    if (window.dentalApp) {
        window.dentalApp.resetAnalysis();
    }
}
