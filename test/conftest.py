import os
import sys

from dotenv import load_dotenv
from testcontainers.postgres import PostgresContainer


container = PostgresContainer("postgres:16-alpine")
container.start()

os.environ["POSTGRES_URL"] = container.get_connection_url()
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_HOURS", "1")

load_dotenv(override=True)

# ensure repository root is on sys.path so tests can import packages like `backend` and `proxy`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
