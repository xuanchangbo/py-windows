import os
import sys
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QLabel, 
                             QProgressBar, QFileDialog, QMessageBox, QCheckBox,
                             QSpinBox, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class ConvertThread(QThread):
    progress = pyqtSignal(int)
    file_converted = pyqtSignal(str, str, float, float, float)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, files, output_folder, keep_original, quality, lossless):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
        self.keep_original = keep_original
        self.quality = quality
        self.lossless = lossless
        self.is_running = True

    def run(self):
        total_files = len(self.files)
        for index, file_path in enumerate(self.files):
            if not self.is_running:
                break
                
            try:
                with Image.open(file_path) as img:
                    # 处理图像模式
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGBA')
                    else:
                        img = img.convert('RGB')

                    # 构建输出路径
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_dir = self.output_folder if self.output_folder else os.path.dirname(file_path)
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"{base_name}.webp")

                    # 保存为WebP
                    img.save(
                        output_path,
                        'WEBP',
                        lossless=self.lossless,
                        quality=self.quality,
                        method=6
                    )

                    # 计算大小变化
                    original_size = os.path.getsize(file_path)
                    new_size = os.path.getsize(output_path)
                    reduction = (1 - new_size / original_size) * 100

                    # 删除原图（如果选择）
                    if not self.keep_original:
                        os.remove(file_path)

                    self.file_converted.emit(file_path, output_path, original_size, new_size, reduction)
                    
            except Exception as e:
                self.error.emit(f"转换失败 {file_path}: {str(e)}")
            
            # 更新进度
            self.progress.emit(int((index + 1) / total_files * 100))
        
        self.finished.emit()

    def stop(self):
        self.is_running = False

class ImageToWebPConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.files = []
        self.output_folder = None
        self.convert_thread = None

    def initUI(self):
        self.setWindowTitle('图片转WebP工具')
        self.setGeometry(100, 100, 800, 600)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 文件列表区域
        file_group = QGroupBox("文件列表")
        file_layout = QVBoxLayout()
        
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        file_layout.addWidget(self.file_list)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("添加图片")
        self.add_button.clicked.connect(self.add_files)
        
        self.remove_button = QPushButton("移除选中")
        self.remove_button.clicked.connect(self.remove_selected)
        
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.clear_button)
        
        file_layout.addLayout(button_layout)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # 设置区域
        settings_group = QGroupBox("转换设置")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("输出质量:"), 0, 0)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        settings_layout.addWidget(self.quality_spin, 0, 1)
        
        self.lossless_check = QCheckBox("无损压缩")
        settings_layout.addWidget(self.lossless_check, 1, 0, 1, 2)
        
        self.keep_original_check = QCheckBox("保留原图")
        self.keep_original_check.setChecked(True)
        settings_layout.addWidget(self.keep_original_check, 2, 0, 1, 2)
        
        self.output_button = QPushButton("选择输出文件夹")
        self.output_button.clicked.connect(self.select_output_folder)
        settings_layout.addWidget(self.output_button, 3, 0, 1, 2)
        
        self.output_label = QLabel("输出目录: 同原文件目录")
        settings_layout.addWidget(self.output_label, 4, 0, 1, 2)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # 进度区域
        progress_group = QGroupBox("转换进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备就绪")
        progress_layout.addWidget(self.status_label)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.convert_button = QPushButton("开始转换")
        self.convert_button.clicked.connect(self.start_conversion)
        
        self.cancel_button = QPushButton("取消转换")
        self.cancel_button.clicked.connect(self.cancel_conversion)
        self.cancel_button.setEnabled(False)
        
        control_layout.addWidget(self.convert_button)
        control_layout.addWidget(self.cancel_button)
        
        progress_layout.addLayout(control_layout)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # 启用拖放功能
        self.setAcceptDrops(True)
        self.file_list.setAcceptDrops(True)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path) and self.is_supported_format(file_path):
                if file_path not in self.files:
                    self.files.append(file_path)
                    self.file_list.addItem(os.path.basename(file_path))
    
    def is_supported_format(self, file_path):
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif')
        return file_path.lower().endswith(supported_formats)
    
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.gif)"
        )
        
        for file_path in files:
            if file_path not in self.files:
                self.files.append(file_path)
                self.file_list.addItem(os.path.basename(file_path))
    
    def remove_selected(self):
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            index = self.file_list.row(item)
            self.file_list.takeItem(index)
            del self.files[index]
    
    def clear_list(self):
        self.file_list.clear()
        self.files = []
    
    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_folder = folder
            self.output_label.setText(f"输出目录: {folder}")
    
    def start_conversion(self):
        if not self.files:
            QMessageBox.warning(self, "警告", "请先添加要转换的图片文件!")
            return
        
        # 禁用UI控件
        self.set_ui_enabled(False)
        
        # 创建转换线程
        self.convert_thread = ConvertThread(
            self.files, 
            self.output_folder, 
            self.keep_original_check.isChecked(),
            self.quality_spin.value(),
            self.lossless_check.isChecked()
        )
        
        # 连接信号
        self.convert_thread.progress.connect(self.progress_bar.setValue)
        self.convert_thread.file_converted.connect(self.on_file_converted)
        self.convert_thread.finished.connect(self.on_conversion_finished)
        self.convert_thread.error.connect(self.on_conversion_error)
        
        # 启动线程
        self.convert_thread.start()
    
    def cancel_conversion(self):
        if self.convert_thread and self.convert_thread.isRunning():
            self.convert_thread.stop()
            self.convert_thread.wait()
            self.status_label.setText("转换已取消")
            self.set_ui_enabled(True)
    
    def on_file_converted(self, input_path, output_path, original_size, new_size, reduction):
        # 更新文件列表中的项目状态
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if os.path.basename(input_path) in item.text():
                item.setText(f"{os.path.basename(input_path)} -> {os.path.basename(output_path)} "
                            f"({original_size/1024:.1f}KB -> {new_size/1024:.1f}KB, 减少: {reduction:.1f}%)")
                break
    
    def on_conversion_finished(self):
        self.status_label.setText("转换完成!")
        self.set_ui_enabled(True)
        QMessageBox.information(self, "完成", "所有图片转换完成!")
    
    def on_conversion_error(self, error_msg):
        self.status_label.setText(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)
    
    def set_ui_enabled(self, enabled):
        self.add_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.convert_button.setEnabled(enabled)
        self.cancel_button.setEnabled(not enabled)
        self.quality_spin.setEnabled(enabled)
        self.lossless_check.setEnabled(enabled)
        self.keep_original_check.setEnabled(enabled)
        self.output_button.setEnabled(enabled)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    converter = ImageToWebPConverter()
    converter.show()
    sys.exit(app.exec_())
