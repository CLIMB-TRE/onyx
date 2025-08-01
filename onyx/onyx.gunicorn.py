"""gunicorn WSGI server configuration."""

from pathlib import Path
import os
from dotenv import load_dotenv
from gunicorn import glogging

chdir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(Path(chdir).parent / ".env")

wsgi_app = "onyx.wsgi"
workers = os.environ["GUNICORN_WORKERS"]
accesslog = "-"
access_log_format = (
    # '%({x-forwarded-for}i)s %(l)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    '%({x-forwarded-for}i)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s ms'
)
logging_format = r"[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s"
glogging.Logger.datefmt = ""
glogging.Logger.error_fmt = "gu.err " + logging_format
glogging.Logger.access_fmt = "gu.acc " + logging_format
glogging.Logger.syslog_fmt = "gu.sys " + logging_format
