# app/main.py

# Load environment before anything else.
# It is required to resolve other imports.
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.api import projects  # noqa: E402
from fastapi import FastAPI  # noqa: E402

app = FastAPI(title="Project Service API")

# Register routers
app.include_router(projects.router)
