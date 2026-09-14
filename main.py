import os
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature

# Configuration des répertoires
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "database.db"

# Sécurité & Authentication
SECRET_KEY = "SUPER_SECRET_KEY_VIP_BETS_CHANGE_ME_IN_PRODUCTION"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY)

app = FastAPI(title="VIP Bets Platform")

# Fichiers statiques & Templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- BASE DE DONNÉES ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table Utilisateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        xbet_id TEXT NOT NULL,
        is_vip BOOLEAN DEFAULT 0,
        is_admin BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Table Pronostics VIP
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_title TEXT NOT NULL,
        league TEXT NOT NULL,
        bet_type TEXT NOT NULL,
        odds REAL NOT NULL,
        confidence TEXT NOT NULL,
        analysis TEXT,
        image_url TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Création d'un compte admin par défaut si inexistant
    cursor.execute("SELECT * FROM users WHERE email = ?", ("admin@vipbets.com",))
    if not cursor.fetchone():
        admin_pass = pwd_context.hash("AdminVIP2026!")
        cursor.execute("""
            INSERT INTO users (full_name, email, password_hash, xbet_id, is_vip, is_admin)
            VALUES (?, ?, ?, ?, 1, 1)
        """, ("Administrateur VIP", "admin@vipbets.com", admin_pass, "0000000"))
    
    conn.commit()
    conn.close()

init_db()

# --- HELPER DE SESSION ---
def get_current_user(request: Request, db: sqlite3.Connection = Depends(get_db)) -> Optional[dict]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        user_id = serializer.loads(session_token, max_age=86400 * 7) # 7 jours
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except BadSignature:
        return None

# --- ROUTES D'AUTHENTIFICATION & PAGES PUBLIQUES ---

@app.get("/", response_class=HTMLResponse)
def page_index(request: Request, db: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.post("/register")
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    xbet_id: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "error": "Cet email est déjà utilisé."
        })
    
    hashed_pwd = pwd_context.hash(password)
    cursor.execute("""
        INSERT INTO users (full_name, email, password_hash, xbet_id, is_vip, is_admin)
        VALUES (?, ?, ?, ?, 0, 0)
    """, (full_name, email.lower().strip(), hashed_pwd, xbet_id.strip()))
    db.commit()
    user_id = cursor.lastrowid

    response = RedirectResponse(url="/pending", status_code=status.HTTP_303_SEE_OTHER)
    token = serializer.dumps(user_id)
    response.set_cookie(key="session", value=token, httponly=True)
    return response

@app.get("/login", response_class=HTMLResponse)
def page_login(request: Request, user: Optional[dict] = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/vip" if user["is_vip"] else "/pending")
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    user = cursor.fetchone()
    
    if not user or not pwd_context.verify(password, user["password_hash"]):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Identifiants invalides."
        })
    
    response = RedirectResponse(
        url="/admin" if user["is_admin"] else ("/vip" if user["is_vip"] else "/pending"),
        status_code=status.HTTP_303_SEE_OTHER
    )
    token = serializer.dumps(user["id"])
    response.set_cookie(key="session", value=token, httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session")
    return response

@app.get("/pending", response_class=HTMLResponse)
def page_pending(request: Request, user: Optional[dict] = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    if user["is_vip"]:
        return RedirectResponse(url="/vip")
    return templates.TemplateResponse("pending.html", {"request": request, "user": user})

# --- ESPACE VIP ---

@app.get("/vip", response_class=HTMLResponse)
def page_vip(request: Request, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not user["is_vip"] and not user["is_admin"]:
        return RedirectResponse(url="/pending", status_code=status.HTTP_303_SEE_OTHER)
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM bets ORDER BY created_at DESC")
    bets = [dict(row) for row in cursor.fetchall()]
    
    return templates.TemplateResponse("vip.html", {"request": request, "user": user, "bets": bets})

# --- PANNEAU ADMINISTRATEUR ---

@app.get("/admin", response_class=HTMLResponse)
def page_admin(request: Request, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE is_admin = 0 ORDER BY created_at DESC")
    users = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM bets ORDER BY created_at DESC")
    bets = [dict(row) for row in cursor.fetchall()]
    
    return templates.TemplateResponse("admin.html", {"request": request, "user": user, "users": users, "bets": bets})

@app.post("/admin/users/{user_id}/validate-vip")
def validate_vip(user_id: int, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_vip = 1 WHERE id = ?", (user_id,))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/users/{user_id}/delete")
def delete_user(user_id: int, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = ? AND is_admin = 0", (user_id,))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/create")
async def create_bet(
    match_title: str = Form(...),
    league: str = Form(...),
    bet_type: str = Form(...),
    odds: float = Form(...),
    confidence: str = Form(...),
    analysis: str = Form(""),
    coupon: Optional[UploadFile] = File(None),
    user: Optional[dict] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    image_url = None
    if coupon and coupon.filename:
        filename = f"{os.urandom(8).hex()}_{coupon.filename}"
        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as f:
            f.write(await coupon.read())
        image_url = f"/static/uploads/{filename}"
    
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO bets (match_title, league, bet_type, odds, confidence, analysis, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (match_title, league, bet_type, odds, confidence, analysis, image_url))
    db.commit()
    
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/{bet_id}/status")
def update_bet_status(
    bet_id: int,
    status_val: str = Form(...),
    user: Optional[dict] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    cursor = db.cursor()
    cursor.execute("UPDATE bets SET status = ? WHERE id = ?", (status_val, bet_id))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/{bet_id}/delete")
def delete_bet(bet_id: int, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    cursor = db.cursor()
    cursor.execute("DELETE FROM bets WHERE id = ?", (bet_id,))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
