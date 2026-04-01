from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import base64
import random
from playwright.async_api import async_playwright

app = FastAPI(title="Perchance NSFW Image API")

class ImageRequest(BaseModel):
    prompt: str
    shape: str = "portrait"  # portrait, landscape, square

@app.get("/")
def read_root():
    return {"message": "Perchance Image API (improved) is running! POST to /generate"}

@app.post("/generate")
async def generate_image(request: ImageRequest):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with async_playwright() as p:
                # Launch browser with more realistic settings to avoid detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    java_script_enabled=True
                )
                
                # Bypass automation detection
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                """)
                
                page = await context.new_page()
                
                # Go to the main generator
                await page.goto("https://perchance.org/ai-text-to-image-generator", wait_until="networkidle", timeout=60000)
                
                # Wait for the prompt textarea and fill it
                await page.wait_for_selector('textarea', timeout=30000)
                textarea = page.locator('textarea').first
                await textarea.fill(request.prompt)
                
                # Click the generate button (adjust selector if needed)
                await page.click('button:has-text("Generate")', timeout=15000)
                
                # Wait for image to appear (this part is flaky)
                await page.wait_for_selector('img', timeout=45000)
                
                # Get the first generated image src
                img = await page.locator('img').first
                image_url = await img.get_attribute('src')
                
                if not image_url or image_url.startswith('data:'):
                    # If it's a data URL, we might need to handle differently
                    raise Exception("Could not extract image URL")
                
                # Download the image
                response = await page.request.get(image_url)
                image_bytes = await response.body()
                
                await browser.close()
                
                b64_string = base64.b64encode(image_bytes).decode('utf-8')
                
                return {
                    "success": True,
                    "image_base64": b64_string,
                    "prompt": request.prompt,
                    "attempt": attempt + 1
                }
                
        except Exception as e:
            await asyncio.sleep(2 ** attempt)  # exponential backoff
            if attempt == max_retries - 1:
                raise HTTPException(status_code=500, detail=f"Generation failed after {max_retries} attempts: {str(e)}")
    
    raise HTTPException(status_code=500, detail="Unknown error")

@app.get("/health")
def health():
    return {"status": "healthy"}
