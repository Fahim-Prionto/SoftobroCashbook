import os
import sys

# Set up paths for cPanel Passenger deployment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Configure Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'softobrocashbook.settings')

# Initialize Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

