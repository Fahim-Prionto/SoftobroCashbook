"""
Startup file for cPanel CloudLinux Python Application wrapper.
Delegates directly to passenger_wsgi.py application entry point.
"""
from passenger_wsgi import application

__all__ = ['application']
