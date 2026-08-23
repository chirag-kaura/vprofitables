import subprocess
import time
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.microsoft import EdgeChromiumDriverManager

def capture_screenshots():
    # Ensure assets dir exists
    os.makedirs('assets', exist_ok=True)

    # Start the server
    print("Starting Vprofitables server...")
    server_process = subprocess.Popen(["python", "app.py"])
    time.sleep(5)  # Wait for server to start

    try:
        print("Initializing Edge WebDriver...")
        options = EdgeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)

        # Dashboard Screenshot
        print("Capturing dashboard.png...")
        driver.set_window_size(1440, 900)
        driver.get("http://localhost:8080")
        time.sleep(3) # wait for DOM and API
        driver.save_screenshot("assets/dashboard.png")
        print("Saved assets/dashboard.png")

        # Mobile Screenshot
        print("Capturing mobile.png...")
        driver.set_window_size(390, 844)
        driver.get("http://localhost:8080")
        time.sleep(3) # wait for DOM and API
        driver.save_screenshot("assets/mobile.png")
        print("Saved assets/mobile.png")

        driver.quit()
    except Exception as e:
        print(f"Error during selenium capture: {e}")
    finally:
        print("Terminating server...")
        server_process.terminate()
        server_process.wait()

if __name__ == '__main__':
    capture_screenshots()
