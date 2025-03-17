import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from PIL import Image, ImageEnhance, ImageFilter, ImageGrab
import pytesseract
import requests
import threading
from functools import partial
import os
import json

class QuestionAnswerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Question Answer App")
        self.geometry("600x500")
        self.resizable(True, True)
        
        # Initialize settings variables
        self.api_key = None
        self.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        # Load settings from file
        self.load_settings()

        # Configure style for a polished look
        self.style = ttk.Style()
        self.style.configure("TButton", padding=5)
        self.style.configure("TLabel", padding=3)

        # Main container
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 10))

        self.new_question_btn = ttk.Button(self.button_frame, text="New Question", command=self.new_question)
        self.new_question_btn.pack(side=tk.LEFT, padx=5)

        self.answer_question_btn = ttk.Button(self.button_frame, text="Answer Question", command=self.answer_question)
        self.answer_question_btn.pack(side=tk.LEFT, padx=5)

        self.settings_btn = ttk.Button(self.button_frame, text="Settings", command=self.open_settings)
        self.settings_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(self.button_frame, text="Clear", command=self.clear_content)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # Content frames
        self.question_frame = ttk.LabelFrame(self.main_frame, text="Question", padding="5")
        self.question_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))

        self.question_text = scrolledtext.ScrolledText(self.question_frame, wrap=tk.WORD, height=2, font=("Arial", 10))
        self.question_text.pack(fill=tk.BOTH, expand=True)

        # System instructions frame
        self.system_frame = ttk.LabelFrame(self.main_frame, text="System Instructions", padding="5")
        self.system_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        self.instructions_label = ttk.Label(self.system_frame, text="Instructions:")
        self.instructions_label.grid(row=0, column=0, sticky=tk.W)

        self.instructions_text = scrolledtext.ScrolledText(self.system_frame, wrap=tk.WORD, height=1, font=("Arial", 10))
        self.instructions_text.grid(row=1, column=0, sticky="nsew")
        self.instructions_text.insert(tk.END, "You are an expert college-level tutor, designed to give short, concise answers in as few characters as possible.")

        self.controls_frame = ttk.Frame(self.system_frame)
        self.controls_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        self.temperature_label = ttk.Label(self.controls_frame, text="Temperature:")
        self.temperature_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        self.temperature_spin = ttk.Spinbox(self.controls_frame, from_=0.0, to=2.0, increment=0.1, format="%.1f", width=10)
        self.temperature_spin.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self.temperature_spin.set(0.0)

        self.max_tokens_label = ttk.Label(self.controls_frame, text="Max Tokens:")
        self.max_tokens_label.grid(row=0, column=2, sticky=tk.W, padx=(0, 5))

        self.max_tokens_spin = ttk.Spinbox(self.controls_frame, from_=1, to=4096, increment=1, width=10)
        self.max_tokens_spin.grid(row=0, column=3, sticky=tk.W)
        self.max_tokens_spin.set(250)

        self.answer_frame = ttk.LabelFrame(self.main_frame, text="Answer", padding="5")
        self.answer_frame.grid(row=3, column=0, columnspan=1, sticky="nsew", padx=5, pady=(5, 0))

        self.answer_text = scrolledtext.ScrolledText(self.answer_frame, wrap=tk.WORD, height=10, font=("Arial", 10))
        self.answer_text.pack(fill=tk.BOTH, expand=True)

        # Bind window close to cleanup
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        """Load API key and Tesseract path from the settings file."""
        settings_dir = os.path.expanduser("~/.question_answer_app")
        settings_file = os.path.join(settings_dir, "settings.json")
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                settings = json.load(f)
                self.api_key = settings.get("api_key", self.api_key)
                self.tesseract_cmd = settings.get("tesseract_cmd", self.tesseract_cmd)

    def save_settings(self):
        """Save API key and Tesseract path to the settings file."""
        settings_dir = os.path.expanduser("~/.question_answer_app")
        os.makedirs(settings_dir, exist_ok=True)
        settings_file = os.path.join(settings_dir, "settings.json")
        with open(settings_file, "w") as f:
            json.dump({"api_key": self.api_key, "tesseract_cmd": self.tesseract_cmd}, f)

    def new_question(self):
        """Initiate the screen selection process."""
        overlay = tk.Toplevel(self)
        overlay.attributes('-fullscreen', True)
        overlay.attributes('-alpha', 0.3)
        overlay.attributes('-topmost', True)
        overlay.grab_set()

        canvas = tk.Canvas(overlay, bg='gray', cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)

        start_x, start_y = 0, 0
        rect_id = None

        def on_mouse_down(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            if rect_id:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

        def on_mouse_drag(event):
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_mouse_up(event):
            end_x, end_y = event.x, event.y
            overlay.grab_release()
            overlay.destroy()
            if abs(end_x - start_x) > 5 and abs(end_y - start_y) > 5:  # Minimum selection size
                self.capture_and_extract(start_x, start_y, end_x, end_y)
            else:
                messagebox.showinfo("Info", "Selected area is too small.")

        def on_cancel(event):
            overlay.grab_release()
            overlay.destroy()

        canvas.bind('<Button-1>', on_mouse_down)
        canvas.bind('<B1-Motion>', on_mouse_drag)
        canvas.bind('<ButtonRelease-1>', on_mouse_up)
        overlay.bind('<Escape>', on_cancel)

    def capture_and_extract(self, x1, y1, x2, y2):
        """Capture screenshot and extract text using OCR."""
        if not self.tesseract_cmd:
            messagebox.showerror("Error", "Tesseract OCR path not set. Please configure in Settings.")
            return

        # Normalize coordinates
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        try:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            image.save('temp-OCR.jpg')
            text = pytesseract.image_to_string(Image.open('temp-OCR.jpg')).strip()
            if text:
                self.question_text.delete('1.0', tk.END)
                self.question_text.insert(tk.END, text)
                self.answer_question_btn.config(state=tk.NORMAL)
            else:
                messagebox.showinfo("Info", "No text extracted from the selected area.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture or process image: {str(e)}. Please check the Tesseract path in Settings.")

    def answer_question(self):
        """Send the question text to Grok3 API and display the answer."""
        if not self.api_key:
            messagebox.showerror("Error", "API key not set. Please configure in Settings.")
            return

        prompt = self.question_text.get('1.0', tk.END).strip()
        if not prompt:
            messagebox.showerror("Error", "No question text to answer.")
            return

        self.answer_question_btn.config(state=tk.DISABLED)
        self.answer_text.delete('1.0', tk.END)
        self.answer_text.insert(tk.END, "Loading...")

        # Perform API call in a separate thread
        threading.Thread(target=self._fetch_answer, args=(prompt,), daemon=True).start()

    def _fetch_answer(self, prompt):
        """Fetch answer from Grok3 API in a background thread."""
        answer = self.get_answer(prompt)
        self.after(0, partial(self.update_answer, answer))

    def get_answer(self, prompt):
        """Make API request to Grok3."""
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        system_content = self.instructions_text.get('1.0', tk.END).strip()
        temperature = float(self.temperature_spin.get())
        max_tokens = int(self.max_tokens_spin.get())
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "grok-2-latest",
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response text")
        except requests.RequestException as e:
            if e.response is not None:
                try:
                    error_detail = e.response.json().get("error", e.response.text)
                except:
                    error_detail = e.response.text
            else:
                error_detail = str(e)
            return f"Error: {error_detail}"

    def update_answer(self, answer):
        """Update the answer text area with the API response."""
        self.answer_text.delete('1.0', tk.END)
        self.answer_text.insert(tk.END, answer)
        self.answer_question_btn.config(state=tk.NORMAL)

    def open_settings(self):
        """Open a dialog to configure the API key and Tesseract path."""
        settings_win = tk.Toplevel(self)
        settings_win.title("Settings")
        settings_win.geometry("400x200")
        settings_win.transient(self)
        settings_win.grab_set()

        frame = ttk.Frame(settings_win, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # API Key Entry
        ttk.Label(frame, text="Grok API Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        api_key_entry = ttk.Entry(frame, width=50, show="*")
        api_key_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)
        if self.api_key:
            api_key_entry.insert(0, self.api_key)

        # Tesseract Path Entry
        ttk.Label(frame, text="Tesseract OCR Path:").grid(row=1, column=0, sticky=tk.W, pady=2)
        tesseract_entry = ttk.Entry(frame, width=50)
        tesseract_entry.grid(row=1, column=1, sticky=tk.EW, pady=2)
        if self.tesseract_cmd:
            tesseract_entry.insert(0, self.tesseract_cmd)

        # Show API Key Checkbox
        show_var = tk.BooleanVar(value=False)
        def toggle_visibility():
            api_key_entry.config(show="" if show_var.get() else "*")
        ttk.Checkbutton(frame, text="Show API Key", variable=show_var, command=toggle_visibility).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Save Button
        def save():
            self.api_key = api_key_entry.get().strip()
            tesseract_path = tesseract_entry.get().strip()
            self.tesseract_cmd = tesseract_path if tesseract_path else None
            self.save_settings()
            settings_win.destroy()
        ttk.Button(frame, text="Save", command=save).grid(row=3, column=0, columnspan=2, pady=10)

        # Configure grid to make the entry fields expandable
        frame.columnconfigure(1, weight=1)

        settings_win.protocol("WM_DELETE_WINDOW", settings_win.destroy)

    def clear_content(self):
        """Clear both content frames and reset button state."""
        self.question_text.delete('1.0', tk.END)
        self.answer_text.delete('1.0', tk.END)
        self.answer_question_btn.config(state=tk.DISABLED)

    def on_closing(self):
        """Handle application shutdown."""
        self.destroy()

if __name__ == "__main__":
    try:
        app = QuestionAnswerApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Startup Error", f"Failed to start application: {str(e)}")