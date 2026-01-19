import sys
import subprocess
import importlib.util
import os

# =============================================================================
# BOOTSTRAPPER: AUTO-INSTALL DEPENDENCIES
# =============================================================================
def check_and_install_dependencies():
    """
    Checks for required packages. If missing, installs them via pip 
    and restarts the script.
    """
    required_packages = {
        'PyQt6': 'PyQt6',  # Import name : Pip package name
        'PIL': 'Pillow'
    }

    missing = []
    for import_name, package_name in required_packages.items():
        if importlib.util.find_spec(import_name) is None:
            missing.append(package_name)

    if missing:
        print(f"Missing dependencies found: {', '.join(missing)}")
        print("Attempting automatic installation...")

        # Try to show a simple GUI message using Tkinter (Standard Lib) 
        # so the user knows something is happening (PyQt isn't available yet).
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw() # Hide main window
            messagebox.showinfo("First Run Setup", 
                                f"Installing required libraries:\n{', '.join(missing)}\n\n"
                                "The app will start automatically once finished.\nCheck console for progress.")
            root.destroy()
        except Exception:
            pass # Fallback to console only if tkinter fails

        # Install dependencies
        try:
            for package in missing:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            
            print("Installation complete. Restarting application...")
            
            # Restart the script to load new libraries
            os.execv(sys.executable, ['python'] + sys.argv)
            
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            input("Press Enter to exit...")
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during setup: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

# Run the check immediately
check_and_install_dependencies()

# =============================================================================
# MAIN APPLICATION
# =============================================================================

import logging
import multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# Now safe to import 3rd party libraries
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                             QProgressBar, QComboBox, QTextEdit, QFileDialog, 
                             QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLineEdit,
                             QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PIL import Image, ImageOps, UnidentifiedImageError

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

STYLESHEET = """
    QMainWindow { background-color: #2b2b2b; color: #f0f0f0; }
    QWidget { font-family: 'Segoe UI', sans-serif; font-size: 14px; }

    QFrame#Panel { background-color: #333; border-radius: 8px; border: 1px solid #444; }

    QLabel.Header { font-size: 16px; font-weight: bold; color: #3498db; margin-bottom: 5px; }
    QLabel.SubText { color: #aaa; font-size: 12px; }

    /* Input Zone */
    QWidget#InputZone { background-color: #3a3a3a; border: 2px dashed #555; border-radius: 10px; }
    QWidget#InputZone:hover { border-color: #3498db; background-color: #404040; }

    QPushButton { background-color: #444; color: white; border: 1px solid #555; 
                  padding: 8px 15px; border-radius: 4px; min-width: 80px; }
    QPushButton:hover { background-color: #505050; border-color: #666; }
    QPushButton:pressed { background-color: #2c3e50; }

    QPushButton#PrimaryBtn { background-color: #2980b9; border: none; font-weight: bold; }
    QPushButton#PrimaryBtn:hover { background-color: #3498db; }

    QPushButton#ActionBtn { background-color: #27ae60; border: none; font-weight: bold; font-size: 15px; padding: 12px; }
    QPushButton#ActionBtn:hover { background-color: #2ecc71; }
    QPushButton#ActionBtn:disabled { background-color: #444; color: #888; }

    QPushButton#CancelBtn { background-color: #c0392b; border: none; }
    QPushButton#CancelBtn:hover { background-color: #e74c3c; }

    QLineEdit, QComboBox { background-color: #222; color: #fff; border: 1px solid #555; 
                           padding: 6px; border-radius: 4px; selection-background-color: #3498db; }

    QProgressBar { border: none; background-color: #222; height: 10px; border-radius: 5px; text-align: center; }
    QProgressBar::chunk { background-color: #3498db; border-radius: 5px; }

    QTextEdit { background-color: #1e1e1e; border: 1px solid #333; color: #ddd; border-radius: 4px; 
                font-family: Consolas, monospace; font-size: 12px; }
"""

def resize_image_task(file_path: Path, output_folder: Path, target_long_side: int) -> str:
    """
    Resizes an image so its longest side is exactly `target_long_side`.
    Performs both Upscaling and Downscaling using LANCZOS resampling.
    """
    try:
        output_path = output_folder / file_path.name

        with Image.open(file_path) as img:

            img = ImageOps.exif_transpose(img)

            if output_path.suffix.lower() in ['.jpg', '.jpeg', '.jfif']:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

            current_w, current_h = img.size

            if current_w >= current_h:

                ratio = target_long_side / current_w
                new_w = target_long_side
                new_h = int(current_h * ratio)
            else:

                ratio = target_long_side / current_h
                new_h = target_long_side
                new_w = int(current_w * ratio)

            if ratio > 1:
                action_type = "Upscaled"
            elif ratio < 1:
                action_type = "Downscaled"
            else:
                action_type = "Copied"

            if ratio != 1.0:
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            img.save(output_path, quality=90, optimize=True)

            return f"{action_type}: {file_path.name} ({current_w}x{current_h} -> {new_w}x{new_h})"

    except UnidentifiedImageError:
        return f"Skipped (Invalid/Corrupt Image): {file_path.name}"
    except Exception as e:
        return f"Error ({file_path.name}): {str(e)}"

class BatchProcessor(QThread):
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, files, output_dir, max_size):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.max_size = max_size
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        total = len(self.files)
        if total == 0:
            self.finished.emit()
            return

        workers = min(total, multiprocessing.cpu_count())

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(resize_image_task, f, self.output_dir, self.max_size): f 
                for f in self.files
            }

            completed_count = 0
            for future in as_completed(futures):
                if not self._is_running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    self.log_message.emit("!!! Operation Cancelled !!!")
                    break

                try:
                    result = future.result()
                    self.log_message.emit(result)
                except Exception as e:
                    self.log_message.emit(f"System Error: {e}")

                completed_count += 1
                self.progress.emit(int((completed_count / total) * 100))

        self.finished.emit()

class DropZone(QWidget):
    files_added = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InputZone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        lbl_icon = QLabel("📂")
        lbl_icon.setStyleSheet("font-size: 48px; border: none; background: transparent;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_text = QLabel("Drag & Drop Images/Folders Here")
        lbl_text.setStyleSheet("font-size: 16px; font-weight: bold; border: none; background: transparent; color: #ccc;")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_add_files = QPushButton("Browse Files")
        self.btn_add_files.setObjectName("PrimaryBtn")
        self.btn_add_files.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_add_folder = QPushButton("Browse Folder")
        self.btn_add_folder.setObjectName("PrimaryBtn")
        self.btn_add_folder.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_layout.addWidget(self.btn_add_files)
        btn_layout.addWidget(self.btn_add_folder)

        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_text)
        layout.addLayout(btn_layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QWidget#InputZone { border-color: #2ecc71; background-color: #3e3e3e; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        if paths:
            self.files_added.emit(paths)
        event.acceptProposedAction()

class ResizerApp(QMainWindow):

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.jfif'}

    def __init__(self):
        super().__init__()
        self.input_files = set()
        self.output_dir = None
        self.worker = None

        self.setup_window()
        self.setup_ui()

    def setup_window(self):
        self.setWindowTitle("Pro Batch Resizer (Upscale/Downscale)")
        self.resize(600, 750)
        self.setStyleSheet(STYLESHEET)

        frame = self.frameGeometry()
        center = self.screen().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        input_frame = QFrame()
        input_frame.setObjectName("Panel")
        frame_layout = QVBoxLayout(input_frame)

        lbl_head = QLabel("1. Image File Input")
        lbl_head.setProperty("class", "Header")
        frame_layout.addWidget(lbl_head)

        self.drop_zone = DropZone()
        self.drop_zone.btn_add_files.clicked.connect(self.browse_files)
        self.drop_zone.btn_add_folder.clicked.connect(self.browse_folder)
        self.drop_zone.files_added.connect(self.process_incoming_paths)
        frame_layout.addWidget(self.drop_zone)

        self.lbl_count = QLabel("Queue: 0 images")
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_count.setProperty("class", "SubText")
        frame_layout.addWidget(self.lbl_count)

        main_layout.addWidget(input_frame)

        settings_frame = QFrame()
        settings_frame.setObjectName("Panel")
        sett_layout = QVBoxLayout(settings_frame)

        lbl_conf = QLabel("2. Configuration")
        lbl_conf.setProperty("class", "Header")
        sett_layout.addWidget(lbl_conf)

        opts_row = QHBoxLayout()

        v_size = QVBoxLayout()
        v_size.addWidget(QLabel("Target Size (Longest Edge):"))
        h_size = QHBoxLayout()
        self.combo_size = QComboBox()

        resolutions = [
            "512", "768", "1024", "1216", "1280", 
            "1600", "1920", "2048", "2432", "3840", "4096"
        ]
        self.combo_size.addItems(resolutions)
        self.combo_size.setCurrentText("1216")

        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("Custom px")
        self.txt_custom.setFixedWidth(80)

        h_size.addWidget(self.combo_size)
        h_size.addWidget(self.txt_custom)
        v_size.addLayout(h_size)
        opts_row.addLayout(v_size)

        v_path = QVBoxLayout()
        v_path.addWidget(QLabel("Output Location:"))
        h_path = QHBoxLayout()
        self.btn_path = QPushButton("Change Folder")
        self.btn_path.clicked.connect(self.choose_output)
        self.lbl_path = QLabel("Default: Source/Resized")
        self.lbl_path.setStyleSheet("color: #aaa; font-style: italic;")
        h_path.addWidget(self.btn_path)
        h_path.addWidget(self.lbl_path)
        v_path.addLayout(h_path)
        opts_row.addLayout(v_path)

        sett_layout.addLayout(opts_row)
        main_layout.addWidget(settings_frame)

        self.btn_process = QPushButton("Start Processing")
        self.btn_process.setObjectName("ActionBtn")
        self.btn_process.clicked.connect(self.start_job)
        main_layout.addWidget(self.btn_process)

        self.btn_cancel = QPushButton("Stop")
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_job)
        main_layout.addWidget(self.btn_cancel)

        self.progress = QProgressBar()
        main_layout.addWidget(self.progress)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        main_layout.addWidget(self.console)

    def browse_files(self):

        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", 
            "All Files (*.*)"
        )
        if files:
            self.process_incoming_paths([Path(f) for f in files])

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.process_incoming_paths([Path(folder)])

    def process_incoming_paths(self, paths: list[Path]):
        """
        Robustly scans folders and files.
        Normalizes extensions to lowercase to handle casing (e.g. .PnG, .JPG).
        Ignores non-image files (movies, docs, etc).
        """
        new_files = []

        for p in paths:

            if p.is_file():
                if p.suffix.lower() in self.EXTENSIONS:
                    new_files.append(p)

            elif p.is_dir():

                for item in p.rglob("*"):
                    if item.is_file():

                        if item.suffix.lower() in self.EXTENSIONS:
                            new_files.append(item)

        initial_count = len(self.input_files)
        self.input_files.update(new_files)
        final_count = len(self.input_files)
        added = final_count - initial_count

        self.lbl_count.setText(f"Queue: {final_count} images")

        if added > 0:
            self.log(f"Added {added} images to queue.")

            if not self.output_dir and self.input_files:
                first_file = next(iter(self.input_files))
                self.output_dir = first_file.parent / "Resized"
                self.lbl_path.setText(f"Output: .../{self.output_dir.name}")
        else:
            self.log("No new valid images found (ignored non-images).")

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_dir = Path(folder)
            self.lbl_path.setText(f"Output: {self.output_dir}")

    def log(self, msg):
        self.console.append(msg)
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def get_target_size(self):
        custom = self.txt_custom.text().strip()
        if custom.isdigit() and int(custom) > 0:
            return int(custom)
        return int(self.combo_size.currentText())

    def start_job(self):
        if not self.input_files:
            QMessageBox.warning(self, "Empty Queue", "Please drag images or folders in first.")
            return

        if not self.output_dir:
            if self.input_files:
                first = next(iter(self.input_files))
                self.output_dir = first.parent / "Resized"
            else:
                 return

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "IO Error", f"Cannot create output folder:\n{e}")
            return

        self.btn_process.setVisible(False)
        self.btn_cancel.setVisible(True)
        self.drop_zone.setEnabled(False)
        self.progress.setValue(0)
        self.console.clear()

        target_size = self.get_target_size()
        self.log(f"Starting batch... Target Longest Side: {target_size}px")
        self.log(f"Mode: Upscale and Downscale allowed (LANCZOS)")
        self.log(f"Destination: {self.output_dir}")

        self.worker = BatchProcessor(list(self.input_files), self.output_dir, target_size)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log_message.connect(self.log)
        self.worker.finished.connect(self.job_finished)
        self.worker.start()

    def cancel_job(self):
        if self.worker:
            self.worker.stop()
            self.log("Stopping...")
            self.btn_cancel.setEnabled(False)
            
    def job_finished(self):
        self.btn_process.setVisible(True)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setEnabled(True)
        self.drop_zone.setEnabled(True)
        self.progress.setValue(100)
        QMessageBox.information(self, "Done", "Batch Processing Complete!")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Ensure the app initializes correctly after the dependency check
    app = QApplication(sys.argv)
    window = ResizerApp()
    window.show()
    sys.exit(app.exec())            