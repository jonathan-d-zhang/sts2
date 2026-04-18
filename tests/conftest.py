import os

# Must be set before any sts2 import so pydantic Settings() validation passes.
os.environ.setdefault("STS2_DATABASE_URL", "postgresql://test:test@localhost/test")
