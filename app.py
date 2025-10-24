from fastapi import FastAPI
from fastapi import File,UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ocr import ocr_parser
import numpy as np
import os
import io
from fastapi.responses import StreamingResponse
import cv2
import requests
from ocr import image_want_from_text
from dotenv import load_dotenv

texts=image_want_from_text
load_dotenv()

app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
unsplash_access_key=os.getenv("ACCESS_KEY")

@app.get("/")
def read_root():
    return {'message':'hello i m a server'}

@app.post("/upload")
async def uploadReceipt(image:UploadFile=File(...)):
    file_bytes=np.frombuffer(await image.read(),np.uint8)
    cv2_img=cv2.imdecode(file_bytes,cv2.IMREAD_COLOR)
    items=ocr_parser(cv2_img)
    return JSONResponse(content={"items":items})



@app.get("/image")
def getFoodImage(food:str):
    url="https://api.unsplash.com/search/photos"
    params={
        "query":food,
        "per_page":1,
        "client_id":unsplash_access_key
    }
    responses=requests.get(url,params=params).json()
    if not responses.get("results"):
        return {"error":"Image not found"}
    image_url=responses["results"][0]["urls"]["small"]
    image_resp=requests.get(image_url)
    if image_resp.status_code != 200:
        return {"error": "Failed to fetch image"}
    return StreamingResponse(io.BytesIO(image_resp.content),media_type="image/jpeg")