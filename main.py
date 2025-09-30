# main.py
import os
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
from io import BytesIO
from PIL import Image
import pytesseract
import openai
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()
# optional google gemini client
try:
    from google import genai
except:
    genai = None

# short names / config
DB = "thetamind.db"
AI_P = os.getenv("AI_PROVIDER", "openai")  # "openai" or "gemini"
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

if OPENAI_KEY:
    openai.api_key = OPENAI_KEY

app = FastAPI(title="thetamind")

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static"
)

@app.on_event("startup")
async def startup_event():
    print("\nRegistered routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", None)
            path = route.path
            print(f"{path} - {methods}")
    print("\n")

# Configure templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# --- DB helper (simple sqlite) ---
def db_init():
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sess (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      usr TEXT,
      qtxt TEXT,
      ocrtxt TEXT,
      ai_res TEXT,
      ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.commit()
    c.close()

db_init() # Initialize the database on startup

def db_ins(usr, q, ocr, ai):
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute("INSERT INTO sess (usr,qtxt,ocrtxt,ai_res) VALUES (?,?,?,?)",
                (usr, q, ocr, ai))
    c.commit()
    c.close()
# --- OCR helper ---
def ocr_img(buf: bytes) -> str:
    img = Image.open(BytesIO(buf)).convert("L")
    # basic preproc
    # img = img.point(lambda p: 255 if p>128 else 0)
    txt = pytesseract.image_to_string(img, lang='eng+vie')
    return txt.strip()

# Root route
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Register route
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Login route
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Tools route
@app.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request):
    return templates.TemplateResponse("tools.html", {"request": request})


async def ai_q(prompt: str) -> str:
    """Helper function to call the appropriate AI provider"""
    if AI_P == "openai" and OPENAI_KEY:
        try:
            # This is a hypothetical call, ensure you are using the correct library version call
            # For example, with newer versions of the openai library:
            # from openai import AsyncOpenAI
            # client = AsyncOpenAI(api_key=OPENAI_KEY)
            # response = await client.chat.completions.create(...)
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI: {str(e)}"
    elif AI_P == "gemini" and GEMINI_KEY and genai is not None:
        try:
            # Gemini implementation would go here
            return "Gemini AI response (not implemented)"
        except Exception as e:
            return f"Error calling Gemini: {str(e)}"
    else:
        return "AI provider not properly configured"

@app.post("/api/ask")
async def api_ask(usr: str = Form(...), txt: str = Form(...), ocr: str = Form("")):
    # call AI (async)
    ans = await ai_q(f"Student: {txt}\nOCR:{ocr}\nTask: give step-by-step solution and hint if stuck.")
    # store session
    try:
        db_ins(usr, txt, ocr, ans)
    except Exception as e:
        print(f"Error storing session: {e}")
    return {"ok": True, "ans": ans}

@app.get("/api/history")
async def api_hist(usr: str):
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute("SELECT id,qtxt,ocrtxt,ai_res,ts FROM sess WHERE usr=? ORDER BY id DESC LIMIT 50", (usr,))
    rows = cur.fetchall()
    c.close()
    res = [{"id":r[0],"q":r[1],"ocr":r[2],"ai":r[3],"ts":r[4]} for r in rows]
    return {"ok": True, "rows": res}

# static sample download
@app.get("/sample")
def sample():
    return FileResponse("static/sample.png", media_type="image/png")

@app.get("/test")
async def test_page():
    return {"message": "Test route is working!"}
