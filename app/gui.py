from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
import sys, os
import threading
import time, requests
from run import app  # Import your Flask app
from flask_cors import CORS 


def run_flask():
    app.run(
        debug=False, 
        host='0.0.0.1',
        port=5000,
        threaded=True
    )


def wait_for_server():
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            response = requests.get('http://127.0.0.1:5000')
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    return False

def main():
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Wait for Flask server to start
    if not wait_for_server():
        print("Error: Could not connect to Flask server")
        sys.exit(1)
    
    # Create Qt Application
    qt_app = QApplication(sys.argv)
    
    # Create WebEngine View
    web = QWebEngineView()
    web.setWindowTitle("YouTube Transcriber")
    web.resize(1200, 800)
    web.setUrl(QUrl("http://127.0.0.1:5000"))
    web.show()
    
    # Start Qt application
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()