"""gunicorn WSGI server configuration."""

from pathlib import Path
import os
from dotenv import load_dotenv

chdir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(Path(chdir).parent / ".env")

wsgi_app = "onyx.wsgi"
access_log_format = (
    '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s'
)

bind = os.environ["GUNICORN_BIND"]
workers = os.environ["GUNICORN_WORKERS"]
accesslog = os.environ["GUNICORN_ACCESS_LOG"]
errorlog = os.environ["GUNICORN_ERROR_LOG"]
