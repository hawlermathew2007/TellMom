import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_URL")
print(DATABASE_URL)
assert DATABASE_URL is not None

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS265")
assert JWT_ALGORITHM is not None

JWT_SECRET = os.getenv("JWT_SECRET")
assert JWT_SECRET is not None

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", 24))
