from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import base64
from perchance import ImageGenerator

app = FastAPI(title="Perchance Open Image API")

class ImageRequest(BaseModel):
    prompt: str
    shape: str = "portrait"  # options: portrait, landscape, square

@app.get("/")
def read_root():
    return {"message": "Perchance Image API is running! Send POST to /generate"}

@app.post("/generate")
async def generate_image(request: ImageRequest):
    try:
        async with ImageGenerator() as gen:
            result = await gen.image(
                prompt=request.prompt,
                shape=request.shape
            )
            
            # Get image as bytes
            image_bytes = await result.download()
            
            # Convert to base64 so n8n can easily handle it
            b64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            return {
                "success": True,
                "image_base64": b64_string,
                "prompt": request.prompt
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optional: Health check endpoint for Render
@app.get("/health")
def health():
    return {"status": "healthy"}
