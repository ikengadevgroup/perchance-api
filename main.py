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
    return {"message": "Perchance API v3 - POST to /generate"}

@app.post("/generate")
async def generate_image(request: ImageRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            context = await browser.new_context(
                viewport={"width": 1366, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            page = await context.new_page()
            
            # Go to page and wait longer for full load
            await page.goto("https://perchance.org/ai-text-to-image-generator", 
                           wait_until="networkidle", timeout=90000)
            
            await asyncio.sleep(5)  # Extra wait for JS to initialize
            
            # Try multiple ways to find the textarea
            textarea = None
            for selector in ['textarea#input', 'textarea', 'input[type="text"]', '[id*="prompt"]']:
                try:
                    textarea = page.locator(selector).first
                    await textarea.wait_for(state="visible", timeout=10000)
                    break
                except:
                    continue
            
            if not textarea:
                raise Exception("Could not find prompt textarea")
            
            await textarea.fill(request.prompt)
            await asyncio.sleep(2)
            
            # Click Generate button using multiple possible selectors
            generate_clicked = False
            for btn_selector in ['button:has-text("Generate")', 'button', '[type="button"]']:
                try:
                    buttons = page.locator(btn_selector)
                    count = await buttons.count()
                    for i in range(count):
                        btn = buttons.nth(i)
                        if await btn.is_visible():
                            await btn.click(timeout=10000)
                            generate_clicked = True
                            break
                    if generate_clicked:
                        break
                except:
                    continue
            
            if not generate_clicked:
                raise Exception("Could not click Generate button")
            
            # Wait longer for image to appear
            await asyncio.sleep(8)
            await page.wait_for_selector("img[src^='http']", timeout=60000)
            
            # Get the first big image
            image_element = page.locator("img").filter(has_not_text="").first
            image_url = await image_element.get_attribute("src")
            
            if not image_url:
                raise Exception("Could not find generated image URL")
            
            # Download image
            response = await page.request.get(image_url)
            image_bytes = await response.body()
            
            await browser.close()
            
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            return {
                "success": True,
                "image_base64": b64[:200] + "..." if len(b64) > 200 else b64,  # shortened for response
                "full_base64_length": len(b64)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")
