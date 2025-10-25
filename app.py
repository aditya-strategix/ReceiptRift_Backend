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
from fastapi.staticfiles import StaticFiles
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
app.mount("/static", StaticFiles(directory="static/dist", html=True), name="static")

@app.get("/")
def read_root():
    return {'message':'hello i m a server'}

@app.post("/upload")
async def uploadReceipt(image: UploadFile = File(...)):
    import traceback, logging
    logger = logging.getLogger("uvicorn.error")
    try:
        # basic sanity checks
        if image is None:
            logger.error("uploadReceipt: missing 'image' field")
            return JSONResponse(status_code=422, content={"error": "missing_field", "detail": "Field 'image' is required"})

        filename = getattr(image, "filename", None)
        content_type = getattr(image, "content_type", None)
        logger.info(f"uploadReceipt: received file filename={filename!r} content_type={content_type!r}")

        file_bytes = await image.read()
        if not file_bytes:
            logger.error("uploadReceipt: uploaded file is empty")
            return JSONResponse(status_code=400, content={"error": "empty_file", "detail": "Uploaded file is empty"})

        # try to decode via OpenCV
        try:
            arr = np.frombuffer(file_bytes, np.uint8)
            cv2_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if cv2_img is None:
                logger.error("uploadReceipt: cv2.imdecode returned None (unsupported/invalid image)")
                return JSONResponse(status_code=400, content={"error": "invalid_image", "detail": "Could not decode uploaded image"})
        except Exception:
            logger.exception("uploadReceipt: error decoding image with OpenCV")
            return JSONResponse(status_code=500, content={"error": "decode_error", "detail": "Failed to decode image"})

        # call OCR parser
        try:
            items = ocr_parser(cv2_img)
        except Exception:
            tb = traceback.format_exc()
            logger.error("uploadReceipt: ocr_parser raised exception:\n%s", tb)
            return JSONResponse(status_code=500, content={"error": "ocr_error", "detail": "OCR parsing failed", "trace": tb})

        logger.info("uploadReceipt: parsed %d items", len(items) if items is not None else 0)
        return JSONResponse(content={"items": items})
    except Exception:
        tb = traceback.format_exc()
        logger.exception("Unexpected error in uploadReceipt")
        return JSONResponse(status_code=500, content={"error": "server_error", "detail": str(tb)})
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Render assigns this dynamically
    uvicorn.run("app:app", host="0.0.0.0", port=port)
