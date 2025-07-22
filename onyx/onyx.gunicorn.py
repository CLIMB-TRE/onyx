"""gunicorn WSGI server configuration."""

from pathlib import Path
import os
from dotenv import load_dotenv

chdir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(Path(chdir) / ".env")

wsgi_app = "onyx.wsgi"

bind = os.environ["GUNICORN_BIND"]
workers = os.environ["GUNICORN_WORKERS"]

# accesslog = os.path.join(chdir, "../access.log")
access_log_format = '%(t)s %(p)s %({x-forwarded-for}i)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s ms'

# errorlog = os.path.join(chdir, "../error.log")
capture_output = True  # Redirect stdout/stderr to errorlog

# daemon = True  # Run process in the background
