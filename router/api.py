from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os
import json

router = APIRouter()

output_dir = "static"
data_dir = "data"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

text_inputs_path = os.path.join(data_dir, "input_text.json")

def read_db_text():
    if os.path.exists(text_inputs_path):
        with open(text_inputs_path, "r") as f:
            return json.load(f)
    return []

def save_db_text(text_inputs):
    with open(text_inputs_path, "w") as f:
        json.dump(text_inputs, f)

def add_text_to_image(image, text: str, filename: str, fontsize: int=40, color: str = 'white') -> str:
    draw = ImageDraw.Draw(image)
    data = read_db_text() 
    # Load a font
    
    font = ImageFont.truetype("arial.ttf", size=fontsize)
    
    # Calculate the bounding box of the text
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Calculate the position to center the text
    text_x = (image.width - text_width) / 2
    text_y = (image.height - text_height) / 2
    text_position = (text_x, text_y)
    
    # Add text to the image
    draw.text(text_position, text, font=font, fill=color)
    
    # Save the modified image to a bytes buffer
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format=image.format)
    img_byte_arr.seek(0)
    
    # Save the modified image to disk
    output_path = os.path.join(output_dir, filename)
    new_data = {"text": text, "path": output_path}
    data.append(new_data)
    save_db_text(data)
    image.save(output_path)

@router.post("/add-text")
async def add_text_to_image_endpoint(file: UploadFile = File(...), text: str = ""):
    if len(text) > 20:
        raise HTTPException(status_code=400, detail="Text length exceeds 20 characters")
    
    if file.content_type.split("/")[0] != "image":
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        add_text_to_image(image, text, file.filename)
        output_path = os.path.join(output_dir, file.filename)
        file_ext = os.path.splitext(output_path)[1].lower()
        valid_extensions = ['.jpg', '.jpeg', '.png']  # Các định dạng hình ảnh hỗ trợ

        if file_ext not in valid_extensions:
            raise ValueError("Unsupported image format")
        with open(output_path, "rb") as img_file:
            base64_img = base64.b64encode(img_file.read()).decode("utf-8")
            http_link = f"data:image/{file_ext[1:]};base64,{urllib.parse.quote_plus(base64_img)}"


        return {"url": http_link}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/get-texts")
async def get_texts():
    text_inputs = read_db_text()
    return {"texts": [entry["text"] for entry in text_inputs]}

@router.get("/check-exist-text")
async def check_text(text: str):
    text_inputs = read_db_text()
    for entry in text_inputs:
        if entry["text"] == text:
            return {"exists": True, "image_url": f"{entry['path']}"}
    return {"exists": False}

# Serve static files
router.mount("/static", StaticFiles(directory=output_dir), name="static")
