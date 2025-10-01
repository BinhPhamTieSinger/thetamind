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
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from urllib.parse import quote, unquote

load_dotenv()

# --- Configuration ---
DB = "thetamind.db"
AI_P = os.getenv("AI_PROVIDER", "openai")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key")

# This is a fallback for when OPENAI is not configured.
# We will use a mock AI response.
IS_AI_CONFIGURED = bool(OPENAI_KEY)

if IS_AI_CONFIGURED:
    import openai
    openai.api_key = OPENAI_KEY

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="thetamind")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    client_kwargs={'scope': 'openid email profile'}
)

# --- Database Initialization ---
def db_init():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT,
        oauth_provider TEXT,
        oauth_id TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        user_id INTEGER NOT NULL,
        node_id TEXT NOT NULL,
        completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, node_id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )""")
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
    encoded_username = request.cookies.get("thetamind_user")
    if encoded_username:
        username = unquote(encoded_username)
        return get_user(username)
    return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# --- AI Interaction ---
async def ai_q(prompt: str) -> str:
    """Helper function to call the appropriate AI provider"""
    if IS_AI_CONFIGURED:
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            # Return error in a JSON format that the frontend can handle
            return json.dumps({"error": f"AI provider error: {e}"})

    # Fallback for demonstration if no API key is set
    await asyncio.sleep(1)
    if "Generate a single math quiz question" in prompt:
         return json.dumps({
            "question": "If a rectangle has a length of (2x + 1) and a width of (x - 3), what is its area in terms of x?",
            "solution": "To find the area of a rectangle, you multiply its length by its width. Area = (2x + 1)(x - 3). Using the FOIL method: (2x * x) + (2x * -3) + (1 * x) + (1 * -3) = 2x² - 6x + x - 3. Combine like terms to get the final area: 2x² - 5x - 3.",
            "difficulty": "Medium"
        })
    elif "You are an expert AI Math Tutor" in prompt:
        return json.dumps({
            "is_correct": True,
            "feedback": "Great job! Your method of using the distributive property (FOIL) is perfect for this problem. You correctly multiplied the terms and combined the like terms to arrive at the correct answer.",
            "smarter_way": "For this type of problem, the FOIL method is the most direct and efficient way to solve it. Keep up the excellent work!"
        })
    return json.dumps({"error": "AI provider not configured."})


# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    hashed_password = get_password_hash(password)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
                    (username, email, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username or email already exists."})
    finally:
        conn.close()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    encoded_username = quote(username)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="thetamind_user", value=encoded_username, httponly=True)
    return response

@app.get('/google-login')
async def google_login(request: Request):
    redirect_uri = request.url_for('auth')
    print(redirect_uri)
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@app.get('/auth')
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    if user_info:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.row_factory = sqlite3.Row
        
        # Check if user already exists in the database
        user = cur.execute("SELECT * FROM users WHERE oauth_provider = 'google' AND oauth_id = ?", (user_info['sub'],)).fetchone()
        
        # If user doesn't exist, insert with a dummy password
        if not user:
            dummy_password = "google_oauth_dummy_password"  # You can use any string here
            hashed_password = get_password_hash(dummy_password)
            cur.execute("INSERT INTO users (username, email, oauth_provider, oauth_id, hashed_password) VALUES (?, ?, 'google', ?, ?)",
                        (user_info['name'], user_info['email'], user_info['sub'], hashed_password))
            conn.commit()
        user = cur.execute("SELECT * FROM users WHERE email=?", (user_info['email'],)).fetchone()
        conn.close()

        user_dict = dict(user)
        encoded_username = quote(user_dict['username'])
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="thetamind_user", value=encoded_username, httponly=True)
        return response
    
    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("thetamind_user")
    return response

@app.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("tools.html", {"request": request, "user": user})

@app.get("/algebra", response_class=HTMLResponse)
async def algebra_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("algebra.html", {"request": request, "user": user})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
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
    if not user:
        return JSONResponse(content={"error": "Authentication required"}, status_code=401)
    
    prompt = f"Generate a single math quiz question on the topic of '{topic}' with a difficulty of '{difficulty}'. Format the response as a JSON object with keys: 'question', 'solution', 'difficulty'."
    ai_response = await ai_q(prompt)
    try:
        return JSONResponse(content=json.loads(ai_response))
    except (json.JSONDecodeError, TypeError):
        return JSONResponse(content={"error": "Failed to generate a valid quiz question from AI."}, status_code=500)


@app.post("/api/evaluate_answer")
async def evaluate_answer(request: Request, question: str = Form(...), user_solution: str = Form(...), correct_solution: str = Form(...), topic: str = Form(...), difficulty: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse(content={"error": "Authentication required"}, status_code=401)

    prompt = f"""As an expert AI Math Tutor, evaluate a student's work.
    Original Question: "{question}"
    Student's Solution: "{user_solution}"
    Correct Solution: "{correct_solution}"
    Analyze the student's process. Identify misconceptions or errors.
    Provide your evaluation as a JSON object with keys: "is_correct" (boolean), "feedback" (constructive paragraph), "smarter_way" (alternative method or encouragement)."""
    ai_response = await ai_q(prompt)

    try:
        evaluation = json.loads(ai_response)
        is_correct = evaluation.get("is_correct", False)

        # Save to database
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO quiz_history (user_id, topic, difficulty, question, user_solution, is_correct)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user["id"], topic, difficulty, question, user_solution, is_correct))
        conn.commit()
        conn.close()

        return JSONResponse(content=evaluation)
    except (json.JSONDecodeError, TypeError):
        return JSONResponse(content={"error": "Failed to get a valid evaluation from AI."}, status_code=500)

@app.get("/coming_soon", response_class=HTMLResponse)
async def coming_soon_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("coming_soon.html", {"request": request, "user": user})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
