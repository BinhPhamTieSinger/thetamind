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
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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

# --- AI wrapper (short) ---
# --- AI wrapper (short) ---
async def ai_q(prompt: str) -> str:
    if AI_P == "openai" and OPENAI_KEY:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini" if hasattr(openai, "ChatCompletion") else "gpt-4o",
                messages=[{"role":"system","content":"You are a concise math tutor. Explain steps."},
                          {"role":"user","content": prompt}],
                temperature=0.2,
                max_tokens=800
            )
            out = resp['choices'][0]['message']['content'].strip()
            return out
        except Exception as e:
            return f"AI_ERR: {e}"
    elif AI_P == "gemini" and GEMINI_KEY and genai:
        try:
            # new correct usage
            client = genai.Client(api_key=GEMINI_KEY)
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            # response object has .text field
            return resp.text
        except Exception as e:
            return f"AI_ERR: {e}"
    else:
        return "AI provider not configured."

# --- API models ---
class AskIn(BaseModel):
    usr: str
    txt: str

# --- Routes ---
@app.on_event("startup")
async def startup():
    db_init()

@app.get("/", response_class=HTMLResponse)
async def idx(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...)):
    b = await file.read()
    try:
        txt = ocr_img(b)
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)})
    return {"ok": True, "txt": txt}

@app.post("/api/ask")
async def api_ask(usr: str = Form(...), txt: str = Form(...), ocr: str = Form("")):
    # call AI (async)
    ans = await ai_q(f"Student: {txt}\nOCR:{ocr}\nTask: give step-by-step solution and hint if stuck.")
    # store session
    try:
        db_ins(usr, txt, ocr, ans)
    except Exception:
        pass
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
