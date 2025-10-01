# main.py
import os
from fastapi import FastAPI, UploadFile, File, Form, Request, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import json
import asyncio
from dotenv import load_dotenv
from passlib.context import CryptContext
from typing import Optional
from starlette.requests import Request
from starlette.responses import Response

load_dotenv()

# --- Configuration ---
DB = "thetamind.db"
AI_P = os.getenv("AI_PROVIDER", "openai")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

IS_AI_CONFIGURED = bool(OPENAI_KEY)

if IS_AI_CONFIGURED:
    import openai
    openai.api_key = OPENAI_KEY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="thetamind")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Database Initialization ---
def db_init():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        question TEXT NOT NULL,
        user_solution TEXT,
        is_correct BOOLEAN,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    conn.commit()
    conn.close()

db_init()

# --- User and Session Management ---
def get_user(username: str):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    return user

def get_current_user(request: Request):
    username = request.cookies.get("thetamind_user")
    if username:
        return get_user(username)
    return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# --- AI Interaction ---
async def ai_q(prompt: str) -> str:
    if IS_AI_CONFIGURED:
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo", messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return json.dumps({"error": f"AI provider error: {e}"})

    await asyncio.sleep(1)
    if "Generate a single math quiz question" in prompt:
        return json.dumps({"question": "If a rectangle has a length of (2x + 1) and a width of (x - 3), what is its area in terms of x?", "solution": "Area = (2x + 1)(x - 3) = 2x² - 5x - 3.", "difficulty": "Medium"})
    elif "You are an expert AI Math Tutor" in prompt:
        return json.dumps({"is_correct": True, "feedback": "Great job! Your method is perfect.", "smarter_way": "The FOIL method is the most direct way."})
    elif "Explain the following math concept" in prompt:
        return json.dumps({"title": "The FOIL Method", "explanation": "FOIL stands for First, Outer, Inner, Last. It's a mnemonic for multiplying two binomials. For (a+b)(c+d), you multiply: First terms (a*c), Outer terms (a*d), Inner terms (b*c), and Last terms (b*d), then sum them up."})
    elif "Solve the following math problem" in prompt:
         return json.dumps({"solution": "To factor x² - 5x + 6, you look for two numbers that multiply to 6 and add to -5. These numbers are -2 and -3. So, the factored form is (x - 2)(x - 3)."})
    return json.dumps({"error": "AI provider not configured."})

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.post("/register")
async def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    print(f"Password: {password}")
    print(f"Length (chars): {len(password)}")
    print(f"Length (bytes): {len(password.encode('utf-8'))}")

    hashed_password = get_password_hash(password)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)", (username, email, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username or email already exists."})
    finally:
        conn.close()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/login")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="thetamind_user", value=username, httponly=True)
    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("thetamind_user")
    return response
    
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request): return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request})

@app.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("tools.html", {"request": request, "user": user})

@app.get("/algebra", response_class=HTMLResponse)
async def algebra_page(request: Request):
    user = get_current_user(request)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("algebra.html", {"request": request, "user": user})

@app.get("/geometry", response_class=HTMLResponse)
async def geometry_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("coming_soon.html", {"request": request, "user": user, "topic": "Geometry"})

@app.get("/calculus", response_class=HTMLResponse)
async def calculus_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("coming_soon.html", {"request": request, "user": user, "topic": "Calculus"})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user: return RedirectResponse(url="/login")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT topic, difficulty, is_correct, COUNT(*) as count FROM quiz_history WHERE user_id = ? GROUP BY topic, difficulty, is_correct", (user["id"],))
    stats = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "stats": stats})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("about.html", {"request": request, "user": user})

# --- API Routes ---
@app.post("/api/generate_quiz")
async def generate_quiz(request: Request, topic: str = Form(...), difficulty: str = Form(...)):
    user = get_current_user(request)
    if not user: return JSONResponse(content={"error": "Authentication required"}, status_code=401)
    prompt = f"Generate a single math quiz question on the topic of '{topic}' with a difficulty of '{difficulty}'. Format the response as a JSON object with keys: 'question', 'solution', 'difficulty'."
    ai_response = await ai_q(prompt)
    try: return JSONResponse(content=json.loads(ai_response))
    except (json.JSONDecodeError, TypeError): return JSONResponse(content={"error": "Failed to generate a valid quiz question from AI."}, status_code=500)

@app.post("/api/evaluate_answer")
async def evaluate_answer(request: Request, question: str = Form(...), user_solution: str = Form(...), correct_solution: str = Form(...), topic: str = Form(...), difficulty: str = Form(...)):
    user = get_current_user(request)
    if not user: return JSONResponse(content={"error": "Authentication required"}, status_code=401)
    prompt = f"""As an expert AI Math Tutor, evaluate a student's work.
    Original Question: "{question}"
    Student's Solution: "{user_solution}"
    Correct Solution: "{correct_solution}"
    Analyze the student's process. Provide your evaluation as a JSON object with keys: "is_correct" (boolean), "feedback" (constructive paragraph), "smarter_way" (alternative method or encouragement)."""
    ai_response = await ai_q(prompt)
    try:
        evaluation = json.loads(ai_response)
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("INSERT INTO quiz_history (user_id, topic, difficulty, question, user_solution, is_correct) VALUES (?, ?, ?, ?, ?, ?)", (user["id"], topic, difficulty, question, user_solution, evaluation.get("is_correct", False)))
        conn.commit()
        conn.close()
        return JSONResponse(content=evaluation)
    except (json.JSONDecodeError, TypeError): return JSONResponse(content={"error": "Failed to get a valid evaluation from AI."}, status_code=500)

@app.post("/api/get_lesson")
async def get_lesson(request: Request, topic: str = Form(...)):
    user = get_current_user(request)
    if not user: return JSONResponse(content={"error": "Authentication required"}, status_code=401)
    prompt = f"Explain the following math concept in a clear, concise way suitable for a student: '{topic}'. Format the response as a JSON object with keys: 'title' and 'explanation'."
    ai_response = await ai_q(prompt)
    try: return JSONResponse(content=json.loads(ai_response))
    except (json.JSONDecodeError, TypeError): return JSONResponse(content={"error": "Failed to generate a valid lesson from AI."}, status_code=500)

@app.post("/api/solve_problem")
async def solve_problem(request: Request, problem: str = Form(...)):
    user = get_current_user(request)
    if not user: return JSONResponse(content={"error": "Authentication required"}, status_code=401)
    prompt = f"Solve the following math problem and provide a step-by-step explanation: '{problem}'. Format the response as a JSON object with a single key: 'solution'."
    ai_response = await ai_q(prompt)
    try: return JSONResponse(content=json.loads(ai_response))
    except (json.JSONDecodeError, TypeError): return JSONResponse(content={"error": "Failed to generate a valid solution from AI."}, status_code=500)

