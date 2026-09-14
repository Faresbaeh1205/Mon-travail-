import os
import sqlite3
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature

# Configuration des dossiers
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / "database.db"

SECRET_KEY = "SUPER_SECRET_KEY_VIP_BETS_2026"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY)

app = FastAPI(title="VIP Bets Platform")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

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
    );""")
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
    );""")
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

# --- GESTION DE SESSION ---
def get_current_user(request: Request, db: sqlite3.Connection = Depends(get_db)) -> Optional[dict]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        user_id = serializer.loads(session_token, max_age=86400 * 7)
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except BadSignature:
        return None

# --- TEMPLATES HTML & STYLES ---
CSS_STYLE = """
:root { --bg: #0b0f19; --card: #151c2c; --green: #00e676; --gold: #ffd700; --text: #f0f4f8; --muted: #94a3b8; --border: #1e293b; --danger: #ff5252; }
* { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
body { background-color: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
.navbar { display:flex; justify-content:space-between; align-items:center; padding:1rem 1.5rem; background:rgba(21, 28, 44, 0.95); border-bottom:1px solid var(--border); position:sticky; top:0; z-index:100; }
.logo { font-size:1.4rem; font-weight:800; color:var(--gold); text-decoration:none; }
.logo span { color:var(--green); }
.nav-links a { color:var(--text); text-decoration:none; margin-left:1rem; font-weight:600; font-size:0.9rem; }
.container { max-width:1100px; margin:0 auto; padding:1.5rem 1rem; width:100%; flex:1; }
.btn { display:inline-block; padding:0.8rem 1.2rem; border-radius:8px; font-weight:700; text-decoration:none; border:none; cursor:pointer; text-align:center; }
.btn-primary { background:linear-gradient(135deg, var(--green), #00b0ff); color:#000; width:100%; margin-top:0.5rem; }
.btn-affiliate { background:linear-gradient(135deg, var(--gold), #ff9100); color:#000; font-size:1rem; width:100%; padding:0.9rem; margin:1rem 0; display:block; }
.btn-danger { background-color:var(--danger); color:#fff; }
.card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:1.2rem; margin-bottom:1.5rem; }
.hero { text-align:center; padding:1.5rem 0; }
.hero h1 { font-size:2rem; color:var(--gold); margin-bottom:0.5rem; }
.hero p { color:var(--muted); font-size:1rem; }
.grid-2 { display:grid; grid-template-columns: 1fr 1fr; gap:1.5rem; }
@media(max-width:768px){ .grid-2 { grid-template-columns:1fr; } }
.form-group { margin-bottom:1rem; }
.form-group label { display:block; margin-bottom:0.4rem; color:var(--muted); font-size:0.85rem; }
.form-group input, .form-group textarea { width:100%; padding:0.75rem; background:#0d121d; border:1px solid var(--border); border-radius:6px; color:#fff; font-size:0.95rem; }
.badge { padding:0.3rem 0.6rem; border-radius:20px; font-size:0.8rem; font-weight:bold; }
.badge-odds { background:rgba(255, 215, 0, 0.15); color:var(--gold); border:1px solid var(--gold); }
.badge-won { background:#00e676; color:#000; }
.badge-lost { background:#ff5252; color:#fff; }
.bet-card { border-left:4px solid var(--green); }
.bet-header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:0.8rem; margin-bottom:1rem; }
.bet-img { width:100%; max-height:400px; object-fit:contain; border-radius:8px; margin-top:1rem; background:#000; }
.analysis-box { background:#0d121d; padding:1rem; border-radius:8px; margin-top:0.8rem; line-height:1.6; white-space: pre-wrap; font-size:0.95rem; }
table { width:100%; border-collapse:collapse; margin-top:1rem; }
th, td { padding:0.75rem; text-align:left; border-bottom:1px solid var(--border); font-size:0.85rem; }
th { color:var(--muted); }
"""

def render_html(title: str, content: str, user: Optional[dict] = None) -> HTMLResponse:
    nav_links = ""
    if user:
        if user.get("is_admin"):
            nav_links += '<a href="/admin">Admin</a>'
        nav_links += '<a href="/vip">Espace VIP</a><a href="/logout">Déconnexion</a>'
    else:
        nav_links += '<a href="/login">Connexion</a><a href="/#register" style="color:var(--green)">S\'inscrire</a>'

    full_page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{CSS_STYLE}</style>
</head>
<body>
    <nav class="navbar">
        <a href="/" class="logo">VIP<span>BETS</span></a>
        <div class="nav-links">{nav_links}</div>
    </nav>
    <div class="container">{content}</div>
</body>
</html>"""
    return HTMLResponse(content=full_page)

# --- ROUTES ---

@app.get("/")
def page_index(request: Request, db: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, db)
    content = """
    <section class="hero">
        <h1>Pronostics Sportifs VIP</h1>
        <p>Rejoignez le club exclusif et accédez aux coupons des experts.</p>
    </section>
    <div class="grid-2">
        <div class="card">
            <h2 style="color:var(--gold); margin-bottom:1rem;">Accès VIP Gratuit à Vie</h2>
            <p style="margin-bottom:1rem; line-height:1.6; color:var(--muted);">
                1. Cliquez sur le bouton ci-dessous pour vous inscrire sur 1xBet.<br>
                2. Utilisez le code promo officiel : <strong style="color:var(--green)">1x_5670093</strong>.<br>
                3. Entrez votre ID parieur dans le formulaire ci-contre.
            </p>
            <a href="https://refpa1376993.top/L?tag=d_3978377m_1573c_&site=3978377&ad=1573" target="_blank" class="btn btn-affiliate">
                S'inscrire sur 1xBet avec le code 1x_5670093
            </a>
        </div>
        <div class="card" id="register">
            <h2 style="margin-bottom:1rem;">Inscription</h2>
            <form action="/register" method="POST">
                <div class="form-group"><label>Nom complet</label><input type="text" name="full_name" required></div>
                <div class="form-group"><label>Adresse Email</label><input type="email" name="email" required></div>
                <div class="form-group"><label>Mot de passe</label><input type="password" name="password" required></div>
                <div class="form-group"><label>ID Parieur 1xBet</label><input type="text" name="xbet_id" required placeholder="ex: 45892011"></div>
                <button type="submit" class="btn btn-primary">Demander mon accès VIP</button>
            </form>
        </div>
    </div>
    """
    return render_html("VIP Bets - Accueil", content, user)

@app.post("/register")
def register(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    xbet_id: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),))
    if cursor.fetchone():
        return render_html("Erreur", "<div class='card'><p style='color:var(--danger)'>Cet email est déjà inscrit.</p></div>")
    
    hashed_pwd = pwd_context.hash(password)
    cursor.execute("INSERT INTO users (full_name, email, password_hash, xbet_id, is_vip, is_admin) VALUES (?, ?, ?, ?, 0, 0)",
                   (full_name, email.lower().strip(), hashed_pwd, xbet_id.strip()))
    db.commit()
    user_id = cursor.lastrowid

    response = RedirectResponse(url="/pending", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="session", value=serializer.dumps(user_id), httponly=True)
    return response

@app.get("/login")
def page_login(user: Optional[dict] = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/vip" if user["is_vip"] else "/pending")
    content = """
    <div style="max-width:400px; margin:2rem auto;" class="card">
        <h2 style="margin-bottom:1.5rem; text-align:center;">Connexion</h2>
        <form action="/login" method="POST">
            <div class="form-group"><label>Email</label><input type="email" name="email" required></div>
            <div class="form-group"><label>Mot de passe</label><input type="password" name="password" required></div>
            <button type="submit" class="btn btn-primary">Se connecter</button>
        </form>
    </div>"""
    return render_html("Connexion VIP", content)

@app.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    user = cursor.fetchone()
    
    if not user or not pwd_context.verify(password, user["password_hash"]):
        return render_html("Erreur", "<div class='card'><p style='color:var(--danger)'>Identifiants invalides.</p></div>")
    
    dest = "/admin" if user["is_admin"] else ("/vip" if user["is_vip"] else "/pending")
    response = RedirectResponse(url=dest, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="session", value=serializer.dumps(user["id"]), httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session")
    return response

@app.get("/pending")
def page_pending(user: Optional[dict] = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    if user["is_vip"]:
        return RedirectResponse(url="/vip")
    
    content = f"""
    <div style="max-width:550px; margin:3rem auto; text-align:center;" class="card">
        <h1 style="color:var(--gold); margin-bottom:1rem;">Compte en attente de vérification</h1>
        <p style="color:var(--muted); margin-bottom:1rem;">Bienvenue <strong>{user['full_name']}</strong> !</p>
        <div style="background:#0d121d; padding:1rem; border-radius:8px; margin-bottom:1rem;">
            ID 1xBet soumis : <strong>{user['xbet_id']}</strong>
        </div>
        <p style="color:var(--muted); font-size:0.9rem;">
            Nous vérifions l'utilisation du code promo <strong>1x_5670093</strong>. La validation prend entre 5 minutes et 2 heures.
        </p>
    </div>"""
    return render_html("Attente de Validation", content, user)

@app.get("/vip")
def page_vip(user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login")
    if not user["is_vip"] and not user["is_admin"]:
        return RedirectResponse(url="/pending")
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM bets ORDER BY created_at DESC")
    bets = [dict(row) for row in cursor.fetchall()]
    
    bets_html = ""
    for b in bets:
        badge_status = ""
        if b["status"] == "WON":
            badge_status = '<span class="badge badge-won">GAGNÉ</span>'
        elif b["status"] == "LOST":
            badge_status = '<span class="badge badge-lost">PERDU</span>'
            
        img_html = f'<img src="{b["image_url"]}" class="bet-img">' if b["image_url"] else ""
        analysis_html = f'<div class="analysis-box"><strong>Analyse complète :</strong><br>{b["analysis"]}</div>' if b["analysis"] else ""
        
        bets_html += f"""
        <div class="card bet-card">
            <div class="bet-header">
                <div>
                    <span style="color:var(--muted); font-size:0.85rem;">{b['league']}</span>
                    <h2 style="font-size:1.3rem;">{b['match_title']}</h2>
                </div>
                <div>
                    <span class="badge badge-odds">Côte: {b['odds']}</span>
                    {badge_status}
                </div>
            </div>
            <p style="margin-bottom:0.5rem;"><strong>Pronostic :</strong> <span style="color:var(--green); font-weight:bold;">{b['bet_type']}</span> | <strong>Confiance :</strong> {b['confidence']}</p>
            {analysis_html}
            {img_html}
        </div>"""
    
    if not bets_html:
        bets_html = "<div class='card'><p style='text-align:center; color:var(--muted)'>Aucun pronostic publié pour le moment.</p></div>"

    content = f"<h1 style='margin-bottom:1.5rem;'>Espace VIP 🔒</h1>{bets_html}"
    return render_html("Espace VIP", content, user)

@app.get("/admin")
def page_admin(user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]:
        return RedirectResponse(url="/login")
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE is_admin = 0 ORDER BY created_at DESC")
    users = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM bets ORDER BY created_at DESC")
    bets = [dict(row) for row in cursor.fetchall()]
    
    users_rows = ""
    for u in users:
        status_badge = '<span class="badge badge-won">VIP</span>' if u["is_vip"] else '<span class="badge badge-lost">En attente</span>'
        val_btn = f'<form action="/admin/users/{u["id"]}/validate" method="POST" style="display:inline;"><button class="btn btn-primary" style="padding:0.3rem 0.6rem; font-size:0.75rem;">Valider VIP</button></form>' if not u["is_vip"] else ""
        
        users_rows += f"""
        <tr>
            <td>{u['full_name']}</td>
            <td>{u['email']}</td>
            <td><strong>{u['xbet_id']}</strong></td>
            <td>{status_badge}</td>
            <td>
                {val_btn}
                <form action="/admin/users/{u['id']}/delete" method="POST" style="display:inline;">
                    <button class="btn btn-danger" style="padding:0.3rem 0.6rem; font-size:0.75rem;">Supprimer</button>
                </form>
            </td>
        </tr>"""

    bets_rows = ""
    for b in bets:
        bets_rows += f"""
        <tr>
            <td>{b['match_title']}</td>
            <td>{b['bet_type']}</td>
            <td>{b['odds']}</td>
            <td>{b['status']}</td>
            <td>
                <form action="/admin/bets/{b['id']}/status" method="POST" style="display:inline;"><input type="hidden" name="status_val" value="WON"><button class="btn btn-primary" style="padding:0.3rem 0.5rem; font-size:0.7rem;">Gagné</button></form>
                <form action="/admin/bets/{b['id']}/status" method="POST" style="display:inline;"><input type="hidden" name="status_val" value="LOST"><button class="btn btn-danger" style="padding:0.3rem 0.5rem; font-size:0.7rem;">Perdu</button></form>
                <form action="/admin/bets/{b['id']}/delete" method="POST" style="display:inline;"><button class="btn btn-danger" style="padding:0.3rem 0.5rem; font-size:0.7rem;">Supprimer</button></form>
            </td>
        </tr>"""

    content = f"""
    <h1 style="margin-bottom:1.5rem;">Panneau Administration</h1>
    
    <div class="card">
        <h2 style="color:var(--gold); margin-bottom:1rem;">Publier un nouveau pronostic avec photo & analyse</h2>
        <form action="/admin/bets/create" method="POST" enctype="multipart/form-data">
            <div class="grid-2">
                <div class="form-group"><label>Match (ex: PSG vs Real Madrid)</label><input type="text" name="match_title" required></div>
                <div class="form-group"><label>Ligue / Compétition</label><input type="text" name="league" placeholder="ex: Ligue des Champions" required></div>
            </div>
            <div class="grid-2">
                <div class="form-group"><label>Option de pari (ex: Victoire PSG)</label><input type="text" name="bet_type" required></div>
                <div class="form-group"><label>Côte (ex: 1.85)</label><input type="number" step="0.01" name="odds" required></div>
            </div>
            <div class="grid-2">
                <div class="form-group"><label>Indice de confiance (ex: 9/10)</label><input type="text" name="confidence" required></div>
                <div class="form-group"><label>Capture d'écran / Photo (Galerie)</label><input type="file" name="coupon" accept="image/*"></div>
            </div>
            <div class="form-group">
                <label>Analyse détaillée du match</label>
                <textarea name="analysis" rows="5" placeholder="Écris ton analyse détaillée ici (statistiques, compositions, forme des équipes...)"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Publier le pronostic dans l'espace VIP</button>
        </form>
    </div>

    <div class="card">
        <h2 style="margin-bottom:1rem;">Membres inscrits à valider</h2>
        <div style="overflow-x:auto;">
            <table>
                <thead><tr><th>Nom</th><th>Email</th><th>ID 1xBet</th><th>Statut</th><th>Actions</th></tr></thead>
                <tbody>{users_rows if users_rows else '<tr><td colspan="5">Aucun membre inscrit.</td></tr>'}</tbody>
            </table>
        </div>
    </div>

    <div class="card">
        <h2 style="margin-bottom:1rem;">Historique des paris</h2>
        <div style="overflow-x:auto;">
            <table>
                <thead><tr><th>Match</th><th>Pari</th><th>Côte</th><th>Statut</th><th>Actions</th></tr></thead>
                <tbody>{bets_rows if bets_rows else '<tr><td colspan="5">Aucun pari publié.</td></tr>'}</tbody>
            </table>
        </div>
    </div>"""
    return render_html("Administration", content, user)

@app.post("/admin/users/{user_id}/validate")
def validate_vip(user_id: int, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_vip = 1 WHERE id = ?", (user_id,))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/users/{user_id}/delete")
def delete_user(user_id: int, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = ? AND is_admin = 0", (user_id,))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/create")
def create_bet(
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
        raise HTTPException(status_code=403)
        
    image_url = None
    if coupon and coupon.filename:
        filename = f"{os.urandom(8).hex()}_{coupon.filename}"
        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(coupon.file, f)
        image_url = f"/static/uploads/{filename}"
    
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO bets (match_title, league, bet_type, odds, confidence, analysis, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (match_title, league, bet_type, odds, confidence, analysis, image_url))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/{bet_id}/status")
def update_bet_status(bet_id: int, status_val: str = Form(...), user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    cursor = db.cursor()
    cursor.execute("UPDATE bets SET status = ? WHERE id = ?", (status_val, bet_id))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/{bet_id}/delete")
def delete_bet(bet_id: int, user: Optional[dict] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    cursor = db.cursor()
    cursor.execute("DELETE FROM bets WHERE id = ?", (bet_id,))
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
