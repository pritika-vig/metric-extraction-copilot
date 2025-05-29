from fastapi import FastAPI
from app.api import projects

app = FastAPI()
app.include_router(projects.router)

@app.get("/")
def read_root():
    return {"message": "Hello World - API Ready"}

