import sys
import threading
import time
from app import create_app, socketio

# Get port from command line or default to 5001
port = 5001
if len(sys.argv) > 1:
    try:
        port = int(sys.argv[1])
    except ValueError:
        pass

app = create_app()

# Set unique session cookie name based on port to avoid conflict on localhost
app.config['SESSION_COOKIE_NAME'] = f'session_{port}'

def start_server():
    # In production/frozen mode, debug should be False
    socketio.run(app, debug=False, host='127.0.0.1', port=port, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        # Packaged mode: Run server in thread, show GUI window
        t = threading.Thread(target=start_server)
        t.daemon = True
        t.start()
        
        try:
            import webview
            # Small delay to ensure server is up
            time.sleep(1)
            webview.create_window('SystemV1', f'http://127.0.0.1:{port}', width=1280, height=800)
            webview.start()
        except ImportError:
            # Fallback if pywebview is missing (shouldn't happen if packaged correctly)
            import webbrowser
            time.sleep(1)
            webbrowser.open(f'http://127.0.0.1:{port}')
            # Keep main thread alive
            while True:
                time.sleep(1)
    else:
        # Development mode
        socketio.run(app, debug=True, host='127.0.0.1', port=port, allow_unsafe_werkzeug=True)
