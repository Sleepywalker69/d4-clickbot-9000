# 🔍 Text Scanner Script

Automatically scan for text on your screen, click when found, and repeat! 🖱️

## 📋 Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- 🔄 Continuously scan for specified text on your screen
- 🖱️ Automatically click when text is found
- ⏱️ Customizable scan intervals and wait times
- 🎨 Optional color mode for better text detection
- 🛑 Easy to stop with GUI button or keyboard shortcut

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.x
- Tesseract OCR

## 📥 Installation

1. Clone this repository or download the script:
   ```
   git clone https://github.com/yourusername/text-scanner.git
   ```

2. Navigate to the script directory:
   ```
   cd text-scanner
   ```

3. Install required Python libraries:
   ```
   pip install PySimpleGUI pytesseract opencv-python numpy Pillow pyautogui keyboard
   ```

4. Install Tesseract OCR:
   - Windows: Download and install from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`

## 🚀 Usage

1. Run the script:
   ```
   python text_scanner.py
   ```

2. Use the GUI to configure your scan settings (see [Configuration](#configuration) below).

3. Click "Save Configuration" to save your settings.

4. Click "Start Scanning" to begin the process.

5. To stop scanning:
   - Click the "Stop Scanning" button, or
   - Press the 'P' key on your keyboard

6. Click "Exit" or close the window to end the program.

## ⚙️ Configuration

In the GUI, you can set:

- 🔲 **Scan Region**: Click "Get" to select the area of the screen to scan.
- 📝 **Target Text**: Enter the text you want to find.
- ⏱️ **Scan Interval**: How often to check for the text (in seconds).
- ⏳ **Post-Click Wait**: How long to wait after clicking before resuming scan (in seconds).
- 🖱️ **Click Interval**: Time between clicks when text is detected (in seconds).
- 🎨 **Color Mode**: Enable for color-based text detection (optional).

## 🔧 Troubleshooting

- If text isn't being detected, try:
  - Adjusting the scan region
  - Enabling/disabling color mode
  - Ensuring the text is clearly visible on screen

- If clicks aren't registering, check:
  - Your system's security settings
  - If the application you're clicking has focus

## ⚠️ Disclaimer

This script is for educational purposes only. Ensure you have permission to use automated clicking tools on your system and in your applications.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check [issues page](https://github.com/yourusername/text-scanner/issues).

## 📜 License

This project is [MIT](https://choosealicense.com/licenses/mit/) licensed.
