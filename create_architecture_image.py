#!/usr/bin/env python3
"""
Convert architecture diagram HTML to PNG image
Requires: pip install selenium pillow
For headless Chrome: brew install --cask google-chrome
"""

import os
import time
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from PIL import Image
    
    print("Creating architecture diagram image...")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Create driver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Load the HTML file
    html_path = Path(__file__).parent / "architecture_diagram.html"
    driver.get(f"file://{html_path}")
    
    # Wait for page to load
    time.sleep(2)
    
    # Take screenshot
    screenshot_path = Path(__file__).parent / "architecture_diagram.png"
    driver.save_screenshot(str(screenshot_path))
    
    # Close driver
    driver.quit()
    
    # Crop the image to remove excess whitespace
    img = Image.open(screenshot_path)
    # You can adjust these values to crop as needed
    # img = img.crop((0, 0, 1400, 900))
    img.save(screenshot_path, optimize=True, quality=95)
    
    print(f"✅ Architecture diagram saved as: {screenshot_path}")
    
except ImportError as e:
    print(f"Error: Missing required packages. Please install:")
    print("pip install selenium pillow")
    print("\nAlternatively, you can:")
    print("1. Open architecture_diagram.html in your browser")
    print("2. Take a screenshot manually")
    print("3. Or use an online HTML to PNG converter")
except Exception as e:
    print(f"Error creating image: {e}")
    print("\nAlternative method:")
    print("1. Open architecture_diagram.html in your browser") 
    print("2. Press Cmd+Shift+4 (Mac) or use Snipping Tool (Windows)")
    print("3. Select the diagram area to capture")