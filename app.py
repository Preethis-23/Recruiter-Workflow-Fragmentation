from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class JD(BaseModel):
    title: str
    description: str

class Resume(BaseModel):
    file_path: str

@app.post("/upload_jd/")
async def upload_jd(jd: JD):
    # Logic to save JD in the database
    return {"message": "JD uploaded successfully"}

@app.post("/upload_resume/")
async def upload_resume(resume: Resume):
    # Logic to parse resume and save details in the database
    return {"message": "Resume uploaded and parsed successfully"}
