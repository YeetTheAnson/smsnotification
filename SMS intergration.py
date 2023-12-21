import os
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk
import threading
from queue import Queue
from PIL import Image, ImageTk

class FileMonitorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("SMS Alert")
        self.master.iconbitmap("appicon.ico")  # Set custom icon

        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, rowspan=8, columnspan=4, sticky="nsew")

        # Create pages
        self.phone_number_page = ttk.Frame(self.notebook)
        self.config_page = ttk.Frame(self.notebook)
        self.start_page = ttk.Frame(self.notebook)

        # Add pages to the notebook
        self.notebook.add(self.phone_number_page, text="Phone Number")
        self.notebook.add(self.config_page, text="Configuration")
        self.notebook.add(self.start_page, text="Start")

        # Variables to store input values
        self.file_path_var = tk.StringVar()
        self.adb_path_var = tk.StringVar()
        self.phone_numbers_var = tk.StringVar()

        # Set default values (you can change these)
        self.file_path_var.set(r"C:\Users\anson\Downloads\CRITICAL.DBF")
        self.adb_path_var.set(r"C:\Users\anson\Downloads\platform-tools_r34.0.5-windows\platform-tools\adb.exe")
        self.phone_numbers_var.set("")

        # Create widgets for the Phone Number page
        tk.Label(self.phone_number_page, text="Phone Numbers (one per line):", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.phone_numbers_text = tk.Text(self.phone_number_page, height=4, width=30, font=("Segoe UI", 10), wrap=tk.WORD, padx=5, pady=5)
        self.phone_numbers_text.grid(row=2, column=1, columnspan=2, pady=5)
        tk.Button(self.phone_number_page, text="Save Phone Numbers", command=self.save_phone_numbers, font=("Segoe UI", 10), bd=0, highlightthickness=0).grid(row=3, column=1, pady=5, sticky="w")
        tk.Button(self.phone_number_page, text="Import Phone Numbers", command=self.import_phone_numbers, font=("Segoe UI", 10), bd=0, highlightthickness=0).grid(row=3, column=2, pady=5, sticky="e")
        self.phone_numbers_text.bind("<KeyRelease>", self.update_phone_numbers)
        tk.Label(self.phone_number_page, text="Number of Valid Phone Numbers:", font=("Segoe UI", 12)).grid(row=4, column=0, sticky="e", padx=10, pady=5)
        self.num_phone_numbers_label = tk.Label(self.phone_number_page, text="0", font=("Segoe UI", 12))
        self.num_phone_numbers_label.grid(row=4, column=1, columnspan=2, pady=5)

        # Create widgets for the Configuration page
        tk.Label(self.config_page, text="File Path:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="e", padx=10, pady=5)
        tk.Entry(self.config_page, textvariable=self.file_path_var, width=30, font=("Segoe UI", 10)).grid(row=0, column=1, columnspan=2, pady=5)
        tk.Button(self.config_page, text="Browse", command=self.browse_file, font=("Segoe UI", 10), bd=0, highlightthickness=0).grid(row=0, column=3, pady=5)
        tk.Label(self.config_page, text="ADB Path:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="e", padx=10, pady=5)
        tk.Entry(self.config_page, textvariable=self.adb_path_var, width=30, font=("Segoe UI", 10)).grid(row=1, column=1, columnspan=2, pady=5)
        tk.Button(self.config_page, text="Browse", command=self.browse_adb, font=("Segoe UI", 10), bd=0, highlightthickness=0).grid(row=1, column=3, pady=5)

        # Create widgets for the Start page
        # Load the resized image for the Start Monitoring button
        image_path = "startmonitor.png"  # Assuming the image is in the same directory
        resized_image = self.resize_image(image_path, (200, 200))
        self.start_monitoring_image = ImageTk.PhotoImage(resized_image)
        tk.Button(self.start_page, image=self.start_monitoring_image, command=self.start_monitoring_thread, bd=0, highlightthickness=0).grid(row=0, column=0, columnspan=2, pady=10)
        tk.Button(self.start_page, text="Clear Logs", command=self.clear_logs, font=("Segoe UI", 12), bd=0, highlightthickness=0).grid(row=1, column=0, columnspan=2, pady=10)
        self.log_text = tk.Text(self.start_page, height=8, width=40, font=("Segoe UI", 10))
        self.log_text.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        # Flag to stop the monitoring thread
        self.stop_thread = False
        # Queue for communication between threads
        self.queue = Queue()
        # Thread object
        self.monitoring_thread_obj = None

        # Modify the geometry to fit all widgets
        self.master.geometry("600x550")  # Adjust the dimensions as needed

        # Bind the protocol for window closure
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.stop_thread = True
        if self.monitoring_thread_obj is not None and self.monitoring_thread_obj.is_alive():
            self.monitoring_thread_obj.join()
        self.master.destroy()

    def resize_image(self, image_path, size):
        original_image = Image.open(image_path)
        resized_image = original_image.resize(size, Image.LANCZOS)  # or Image.Resampling.LANCZOS
        return resized_image

    def browse_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path_var.set(file_path)

    def browse_adb(self):
        adb_path = filedialog.askopenfilename()
        if adb_path:
            self.adb_path_var.set(adb_path)

    def log_message(self, message):
        self.queue.put(lambda: self.log_text.insert(tk.END, f"{message}\n"))
        self.queue.put(lambda: self.log_text.see(tk.END))

    def clear_logs(self):
        self.log_text.delete(1.0, tk.END)

    def monitoring_thread(self):
        file_path = self.file_path_var.get()
        adb_path = self.adb_path_var.get()
        phone_numbers_text = self.phone_numbers_var.get()
        phone_numbers = [p.strip() for p in phone_numbers_text.splitlines()]

        last_modified_time = os.path.getmtime(file_path)

        while not self.stop_thread:
            time.sleep(1)
            current_modified_time = os.path.getmtime(file_path)

            if current_modified_time != last_modified_time:
                self.queue.put(lambda: self.log_message("Changes made"))
                for pnumber in phone_numbers:
                    sms_uri = "sms:" + pnumber
                    subprocess.run([adb_path, "shell", "am", "start", "-a", "android.intent.action.SENDTO", "-d", sms_uri, "--es", "sms_body", "Changes\\ made", "--ez", "exit_on_sent", "true"])
                    time.sleep(2)
                    subprocess.run([adb_path, "shell", "input", "tap", "650", "1530"])

                last_modified_time = current_modified_time
            else:
                self.queue.put(lambda: self.log_message("No changes"))

    def process_queue(self):
        while not self.queue.empty():
            self.queue.get()()

    def start_monitoring_thread(self):
        # Create a new thread for monitoring only if it's not already running
        if self.monitoring_thread_obj is None or not self.monitoring_thread_obj.is_alive():
            self.stop_thread = False
            self.monitoring_thread_obj = threading.Thread(target=self.monitoring_thread)
            self.monitoring_thread_obj.start()
            self.master.after(100, self.check_queue)

    def check_queue(self):
        if self.master.winfo_exists():
          self.process_queue()
        if self.monitoring_thread_obj.is_alive():
            self.master.after(100, self.check_queue)


    def update_phone_numbers(self, event):
        phone_numbers_text = self.phone_numbers_text.get("1.0", tk.END)
        phone_numbers = [p.strip() for p in phone_numbers_text.splitlines() if 8 <= len(p.strip()) <= 14]
        self.phone_numbers_var.set("\n".join(phone_numbers))
        self.num_phone_numbers_label.config(text=str(len(phone_numbers)))

    def save_phone_numbers(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.phone_numbers_var.get())

    def import_phone_numbers(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, 'r') as file:
                phone_numbers = file.read()
                self.phone_numbers_text.delete("1.0", tk.END)  # Clear existing text
                self.phone_numbers_text.insert(tk.END, phone_numbers)
                self.update_phone_numbers(None)  # Trigger update to refresh the count

if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap("appicon.ico")  # Set custom icon for the main window
    app = FileMonitorApp(root)
    root.mainloop()
input("Press Enter to exit...")