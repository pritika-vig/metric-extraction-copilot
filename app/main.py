from app.api import projects
from fastapi import FastAPI

app = FastAPI()
app.include_router(projects.router)


@app.get("/")
def read_root():
    return {"message": "Hello World - API Ready"}
