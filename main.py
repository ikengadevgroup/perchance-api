from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import base64
from playwright.async_api import async_playwright

app = FastAPI(title="Perchance Image API")

class ImageRequest(BaseModel):
    prompt: str
    shape: str = "portrait"

@app.get("/")
def read_root():
    return {"message": "Perchance API running - POST to /generate"}

@app.post("/generate")
async def generate_image(request: ImageRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Go to the main generator
            await page.goto("https://perchance.org/ai-text-to-image-generator", wait_until="domcontentloaded", timeout=60000)
            
            # Fill the prompt
            await page.wait_for_selector("textarea", timeout=30000)
            await page.fill("textarea", request.prompt)
            
            # Click Generate button (text-based, more reliable)
            await page.get_by_role("button", name="Generate").click(timeout=15000)
            
            # Wait for image to appear (up to 45 seconds)
            await page.wait_for_selector("img[src^='https']", timeout=45000)
            
            # Get the generated image URL
            image_element = page.locator("img").first
            image_url = await image_element.get_attribute("src")
            
            if not image_url:
                raise Exception("Could not find generated image")
            
            # Download the image
            response = await page.request.get(image_url)
            image_bytes = await response.body()
            
            await browser.close()
            
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            return {
                "success": True,
                "image_base64": b64,
                "prompt": request.prompt
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")
