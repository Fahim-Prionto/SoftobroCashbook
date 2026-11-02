import os
import sys
import traceback

# Base project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load .env file explicitly
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except Exception:
    pass

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'softobrocashbook.settings')

# Initialize WSGI with detailed error-logging wrapper
try:
    from django.core.wsgi import get_wsgi_application
    _django_app = get_wsgi_application()

    def application(environ, start_response):
        try:
            return _django_app(environ, start_response)
        except Exception as e:
            error_trace = traceback.format_exc()
            log_file = os.path.join(BASE_DIR, 'passenger_error.log')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Request Exception ---\n{error_trace}\n")
            raise

except Exception as e:
    startup_trace = traceback.format_exc()
    log_file = os.path.join(BASE_DIR, 'passenger_error.log')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n--- Startup Exception ---\n{startup_trace}\n")

    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = f"""
        <html>
        <head><title>500 Application Startup Error</title></head>
        <body style="font-family: monospace; padding: 30px; background: #fff5f5; color: #900;">
            <h2>500 Application Startup Error on cPanel</h2>
            <p>Django failed to start. Below is the traceback:</p>
            <pre style="background: #fff; padding: 20px; border: 1px solid #fcc; border-radius: 6px; overflow-x: auto;">{startup_trace}</pre>
        </body>
        </html>
        """.encode('utf-8')
        response_headers = [
            ('Content-type', 'text/html; charset=utf-8'),
            ('Content-Length', str(len(output)))
        ]
        start_response(status, response_headers)
        return [output]
