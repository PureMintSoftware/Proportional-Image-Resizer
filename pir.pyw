import os
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

class ImageResizer:
    def __init__(self, master):
        self.master = master
        self.master.title("Proportional Image Resizer")
        self.master.geometry("465x350")
        self.master.bind("<Configure>", self.on_configure)

        self.selected_folder = ""

        self.browse_button = tk.Button(self.master, text="Select Folder Containing Input Images", command=self.browse_folder, width=50, bg="lightblue")
        self.browse_button.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

        self.max_size_label = tk.Label(self.master, text="New Size of Longest Side (pixels):")
        self.max_size_label.grid(row=1, column=0, pady=10, padx=10, sticky="w")

        self.max_size_entry = tk.Entry(self.master, width=40)
        self.max_size_entry.grid(row=1, column=1, pady=10, padx=10, sticky="ew")
        self.max_size_entry.insert(0, "1920")

        self.resize_button = tk.Button(self.master, text="Resize Images", command=self.resize_images, width=50, bg="lightblue")
        self.resize_button.grid(row=2, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.master, variable=self.progress_var, length=350, mode='determinate')
        self.progress_bar.grid(row=3, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

        self.feedback_text = tk.Text(self.master, height=10, width=50, state="disabled")
        self.feedback_text.grid(row=4, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

    def on_configure(self, event):
        if self.master.state() == 'zoomed':
            self.master.geometry("")

    def browse_folder(self):
        self.feedback_text.config(state="normal")
        self.feedback_text.delete(1.0, tk.END)
        self.feedback_text.config(state="disabled")

        self.selected_folder = filedialog.askdirectory()
        self.feedback("Input Folder: " + self.selected_folder)
        self.feedback("Output Folder: " + self.selected_folder + "\Resized")

    def resize_images(self):
        if not self.selected_folder:
            self.feedback("Please select a folder first.")
            return

        max_size = self.get_max_size()
        if max_size is None:
            self.feedback("Please enter a valid max size.")
            return

        image_files = self.get_image_files(self.selected_folder)
        total_images = len(image_files)

        if total_images == 0:
            self.feedback("No image files found in the selected folder.")
            return

        output_folder = os.path.join(self.selected_folder, "Resized")
        for index, file_path in enumerate(image_files, start=1):
            output_path = os.path.join(output_folder, os.path.relpath(file_path, self.selected_folder))
            self.resize_image(file_path, output_path, max_size)

            progress_value = (index / total_images) * 100
            self.progress_var.set(progress_value)
            self.master.update_idletasks()

    def feedback(self, message):
        formatted_message = message.replace("/", "\\")
        self.feedback_text.config(state="normal")
        self.feedback_text.insert(tk.END, formatted_message + "\n")
        self.feedback_text.see(tk.END)
        self.feedback_text.config(state="disabled")

    def get_max_size(self):
        try:
            max_size = int(self.max_size_entry.get())
            return max_size
        except ValueError:
            return None

    def get_image_files(self, folder):
        image_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    image_files.append(os.path.join(root, file))
        return image_files

    def resize_image(self, file_path, output_path, max_size):
        try:
            file_name = os.path.basename(file_path)

            image = Image.open(file_path)
            width, height = image.size

            longest_dimension = max(width, height)

            if longest_dimension != max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))

                resized_image = image.resize((new_width, new_height), resample=Image.LANCZOS)

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                resized_image.save(output_path)

                output_dir = os.path.dirname(output_path).replace(self.selected_folder, '').lstrip('\\').lstrip('/')
                feedback_output_path = os.path.join(output_dir, file_name)

                self.feedback(f"{file_name} resized and saved.")

            else:
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)
                with open(file_path, 'rb') as src_file:
                    with open(output_path, 'wb') as dest_file:
                        while True:
                            chunk = src_file.read(1024 * 1024)
                            if not chunk:
                                break
                            dest_file.write(chunk)
                self.feedback(f"{file_name} copied without resizing.")
        except Exception as e:
            self.feedback(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizer(root)
    root.mainloop()
