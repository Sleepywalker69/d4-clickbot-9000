import PySimpleGUI as sg
import pytesseract
import cv2
import numpy as np
import json
import os
import threading
import time
import win32gui
import win32api
import win32con
import keyboard
import logging
import tkinter as tk
from PIL import ImageGrab
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import re
import ctypes
import pyautogui
import random

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

CONFIG_FILE = 'd4_clickbot_config.json'

# Set up logging
logging.basicConfig(filename='d4_clickbot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class Config:
    scan_region: Tuple[int, int, int, int]
    target_text: str
    scan_interval: float
    post_click_wait: float
    click_interval: float
    color_mode: bool
    killswitch_key: str  # New field for killswitch key

def load_config() -> Config:
    default_config = Config(
        scan_region=(0, 0, 0, 0),
        target_text="",
        scan_interval=1.0,
        post_click_wait=5.0,
        click_interval=0.5,
        color_mode=False,
        killswitch_key='p'  # Default killswitch key
    )
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config_dict = json.load(f)
            default_config_dict = asdict(default_config)
            default_config_dict.update(config_dict)
            return Config(**default_config_dict)
    except json.JSONDecodeError:
        logging.error(f"Error decoding {CONFIG_FILE}. Using default configuration.")
    except KeyError as e:
        logging.error(f"Missing key in configuration: {e}. Using default configuration.")
    return default_config

def save_config(config: Config) -> None:
    with open(CONFIG_FILE, 'w') as f:
        json.dump(asdict(config), f)
    logging.info("Configuration saved successfully.")

def get_screen_scale_factor():
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return user32.GetDpiForSystem() / 96.0

def capture_screen_region(region: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    try:
        scale_factor = get_screen_scale_factor()
        scaled_region = tuple(int(x * scale_factor) for x in region)
        screenshot = ImageGrab.grab(bbox=scaled_region)
        return np.array(screenshot)
    except Exception as e:
        logging.error(f"Error capturing screen region: {e}")
        return None

def preprocess_image(image: np.ndarray, color_mode: bool) -> np.ndarray:
    if color_mode:
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        lower_cream = np.array([10, 20, 80])
        upper_cream = np.array([40, 255, 255])
        mask = cv2.inRange(hsv, lower_cream, upper_cream)
        result = cv2.bitwise_and(image, image, mask=mask)
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        gray = cv2.equalizeHist(gray)
        _, binary_image = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        kernel = np.ones((3, 3), np.uint8)
        binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
        return binary_image

def scan_for_text(region: Tuple[int, int, int, int], color_mode: bool) -> str:
    image = capture_screen_region(region)
    if image is None:
        logging.error("Failed to capture screen region")
        return ""
    processed_image = preprocess_image(image, color_mode)
    try:
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        logging.info(f"OCR result: {text.strip()}")
        return text.strip()
    except Exception as e:
        logging.error(f"Error scanning for text: {e}")
        return ""

class TextScanProcess(threading.Thread):
    def __init__(self, config: Config, window: sg.Window):
        super().__init__()
        self.config = config
        self.window = window
        self.stop_event = threading.Event()
        
    def run(self) -> None:
        while not self.stop_event.is_set():
            self.scan_and_click_phase()
            if self.stop_event.is_set():
                break
            self.post_click_wait_phase()

    def scan_and_click_phase(self) -> None:
        while not self.stop_event.is_set():
            try:
                scanned_text = scan_for_text(self.config.scan_region, self.config.color_mode)
                self.window.write_event_value('-UPDATE-', f"Scanned text: {scanned_text}")
                
                if self.flexible_match(self.config.target_text, scanned_text):
                    self.window.write_event_value('-UPDATE-', f"Target text found: {self.config.target_text}")
                    self.click_until_text_gone()
                    break  # Exit the scanning loop after clicking
                
                time.sleep(self.config.scan_interval)
            except Exception as e:
                logging.error(f"Error in text scan process: {e}")
                self.window.write_event_value('-UPDATE-', f"Error occurred: {e}")
                time.sleep(5)  # Wait before retrying

    def post_click_wait_phase(self) -> None:
        self.window.write_event_value('-UPDATE-', f"Waiting for {self.config.post_click_wait} seconds before resuming scan...")
        time.sleep(self.config.post_click_wait)

    def flexible_match(self, target: str, text: str) -> bool:
        target = target.lower()
        text = text.lower()
        
        def normalize_spaces(s: str) -> str:
            return re.sub(r'\s+', ' ', s).strip()
        
        target = normalize_spaces(target)
        text = normalize_spaces(text)
        
        target_words = target.split()
        
        def partial_word_match(word: str, text: str) -> bool:
            if word in text:
                return True
            min_match_length = max(3, len(word) // 2)
            for i in range(len(text) - min_match_length + 1):
                if text[i:i+min_match_length] in word:
                    return True
            return False
        
        text_words = text.split()
        matched_words = set()
        
        for target_word in target_words:
            if any(partial_word_match(target_word, text_word) for text_word in text_words):
                matched_words.add(target_word)
        
        return len(matched_words) == len(target_words)

    def click_until_text_gone(self) -> None:
        clicks = 0
        while not self.stop_event.is_set():
            try:
                x1, y1, x2, y2 = self.config.scan_region
                click_x = random.randint(x1, x2)
                click_y = random.randint(y1, y2)
                pyautogui.click(click_x, click_y)
                clicks += 1
                self.window.write_event_value('-UPDATE-', f"Clicked at coordinates: ({click_x}, {click_y}). Total clicks: {clicks}")
                
                time.sleep(self.config.click_interval)
                
                scanned_text = scan_for_text(self.config.scan_region, self.config.color_mode)
                if not self.flexible_match(self.config.target_text, scanned_text):
                    self.window.write_event_value('-UPDATE-', f"Target text no longer detected after {clicks} clicks.")
                    break
            except Exception as e:
                logging.error(f"Error clicking within region: {e}")
                self.window.write_event_value('-UPDATE-', f"Error clicking within region: {e}")
                break

    def stop(self) -> None:
        self.stop_event.set()

def get_scan_region():
    root = tk.Tk()
    root.attributes('-alpha', 0.3)
    root.attributes('-fullscreen', True)
    root.configure(background='grey')

    canvas = tk.Canvas(root, cursor="cross")
    canvas.pack(fill=tk.BOTH, expand=True)

    rect = None
    start_x = start_y = 0
    region = None

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect
        start_x, start_y = event.x, event.y
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

    def on_mouse_move(event):
        nonlocal rect
        if rect:
            canvas.delete(rect)
            rect = canvas.create_rectangle(start_x, start_y, event.x, event.y, outline='red', width=2)

    def on_mouse_up(event):
        nonlocal region
        end_x, end_y = event.x, event.y
        region = (min(start_x, end_x), min(start_y, end_y), 
                  max(start_x, end_x), max(start_y, end_y))
        root.quit()

    def on_key(event):
        if event.keysym == 'Escape':
            root.quit()

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    root.bind("<Key>", on_key)

    root.mainloop()
    root.destroy()

    return region

def create_main_window(config: Config) -> sg.Window:
    layout = [
        [sg.Text("d4-clickbot-9000 Configuration")],
        [sg.Text("Scan Region:"), sg.Input(key='SCAN_REGION', default_text=','.join(map(str, config.scan_region)), size=(20, 1)), sg.Button("Get", key='GET_SCAN_REGION')],
        [sg.Text("Target Text:"), sg.Input(key='TARGET_TEXT', default_text=config.target_text, size=(30, 1))],
        [sg.Text("Scan Interval (seconds):"), sg.Input(key='SCAN_INTERVAL', default_text=str(config.scan_interval), size=(5, 1))],
        [sg.Text("Post-Click Wait (seconds):"), sg.Input(key='POST_CLICK_WAIT', default_text=str(config.post_click_wait), size=(5, 1))],
        [sg.Text("Click Interval (seconds):"), sg.Input(key='CLICK_INTERVAL', default_text=str(config.click_interval), size=(5, 1))],
        [sg.Text("Killswitch Key:"), sg.Input(key='KILLSWITCH_KEY', default_text=config.killswitch_key, size=(5, 1))],  # New input for killswitch key
        [sg.Checkbox("Use Color Mode", default=config.color_mode, key='COLOR_MODE')],
        [sg.Button("Save Configuration"), sg.Button("Start Scanning"), sg.Button("Stop Scanning"), sg.Button("Exit")],
        [sg.Multiline(size=(60, 10), key="-OUTPUT-", disabled=True)]
    ]
    window = sg.Window("d4-clickbot-9000", layout, finalize=True)
    return window

def validate_config(config: Config) -> bool:
    if config.scan_region == (0, 0, 0, 0):
        return False
    if not config.target_text:
        return False
    if config.scan_interval <= 0:
        return False
    if config.post_click_wait < 0:
        return False
    if config.click_interval <= 0:
        return False
    if not config.killswitch_key:
        return False
    return True

def main():
    config = load_config()
    window = create_main_window(config)
    scan_process = None

    while True:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED or event == "Exit":
            break
        elif event == 'GET_SCAN_REGION':
            window.hide()
            region = get_scan_region()
            window.un_hide()
            if region:
                window['SCAN_REGION'].update(','.join(map(str, region)))
            else:
                window['-OUTPUT-'].print("Region selection cancelled or no region selected.")
        elif event == "Save Configuration":
            try:
                new_config = Config(
                    scan_region=tuple(map(int, values['SCAN_REGION'].split(','))),
                    target_text=values['TARGET_TEXT'],
                    scan_interval=float(values['SCAN_INTERVAL']),
                    post_click_wait=float(values['POST_CLICK_WAIT']),
                    click_interval=float(values['CLICK_INTERVAL']),
                    color_mode=values['COLOR_MODE'],
                    killswitch_key=values['KILLSWITCH_KEY']  # Save the new killswitch key
                )
                if validate_config(new_config):
                    save_config(new_config)
                    config = new_config
                    window['-OUTPUT-'].print("Configuration saved successfully.")
                else:
                    window['-OUTPUT-'].print("Invalid configuration. Please check all fields.")
            except ValueError:
                window['-OUTPUT-'].print("Invalid input. Please check all fields.")
        elif event == "Start Scanning":
            if scan_process is None or not scan_process.is_alive():
                if validate_config(config):
                    scan_process = TextScanProcess(config, window)
                    scan_process.start()
                    window['-OUTPUT-'].print("Text scanning process started.")
                else:
                    window['-OUTPUT-'].print("Invalid configuration. Please check all fields.")
            else:
                window['-OUTPUT-'].print("Scanning process is already running.")
        elif event == "Stop Scanning":
            if scan_process and scan_process.is_alive():
                scan_process.stop()
                scan_process.join()
                scan_process = None
                window['-OUTPUT-'].print("Scanning process stopped.")
            else:
                window['-OUTPUT-'].print("No scanning process is running.")
        elif event == '-UPDATE-':
            window['-OUTPUT-'].print(values['-UPDATE-'])
        
        if keyboard.is_pressed(config.killswitch_key) and scan_process and scan_process.is_alive():
            scan_process.stop()
            scan_process.join()
            scan_process = None
            window['-OUTPUT-'].print(f"Scanning process terminated by user ({config.killswitch_key} key pressed)")

    if scan_process and scan_process.is_alive():
        scan_process.stop()
        scan_process.join()

    window.close()

if __name__ == "__main__":
    main()