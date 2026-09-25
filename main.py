import os
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, status, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ------------------------------------------------------------------
# CONFIGURATION ET CONNEXION SUPABASE (POOLED IPV4 WITH PSYCOPG2)
# ------------------------------------------------------------------
DEFAULT_DB_URL = "postgresql+psycopg2://postgres.rsnrnxocfwbdepqvyigc:Mamapapa2024%40%40%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# Correction dynamique du driver dialecte pour SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "connect_timeout": 15
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------------------------------------------------------
# MODÈLES DE DONNÉES (POSTGRESQL)
# ------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    xbet_id = Column(String, nullable=False)
    is_vip = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    match_title = Column(String, nullable=False)
    league = Column(String, nullable=False)
    bet_type = Column(String, nullable=False)
    odds = Column(Float, nullable=False)
    confidence = Column(String, nullable=False)
    analysis = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

Base.metadata.create_all(bind=engine)

SECRET_KEY = "SUPER_SECRET_KEY_VIP_BETS_2026"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY)

app = FastAPI(title="VIP Bets Platform")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_admin():
    """Initialise l'administrateur s'il n'existe pas encore dans la base."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@vipbets.com").first()
        if not admin:
            admin_pass = pwd_context.hash("AdminVIP2026!")
            admin_user = User(
                full_name="Administrateur VIP",
                email="admin@vipbets.com",
                password_hash=admin_pass,
                xbet_id="0000000",
                is_vip=True,
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Info Admin Init: {e}")
    finally:
        db.close()

init_admin()

# ------------------------------------------------------------------
# ROUTES PUSHALERT SERVICE WORKER
# ------------------------------------------------------------------
SW_CONTENT = 'importScripts("https://cdn.pushalert.co/sw-91255.js");'

@app.get("/sw.js", include_in_schema=False)
def get_sw():
    return Response(content=SW_CONTENT, media_type="application/javascript")

@app.get("/sw-91255.js", include_in_schema=False)
def get_sw_direct():
    return Response(content=SW_CONTENT, media_type="application/javascript")

# ------------------------------------------------------------------
# SESSIONS ET INTERFACE
# ------------------------------------------------------------------
def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[dict]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        user_id = serializer.loads(session_token, max_age=86400 * 7)
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "password_hash": user.password_hash,
                "xbet_id": user.xbet_id,
                "is_vip": user.is_vip,
                "is_admin": user.is_admin,
            }
        return None
    except BadSignature:
        return None

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
.badge-pending { background:#94a3b8; color:#000; }
.bet-card { border-left:4px solid var(--green); }
.bet-header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:0.8rem; margin-bottom:1rem; }
.bet-img { width:100%; max-height:450px; object-fit:contain; border-radius:8px; margin-top:1rem; background:#000; }
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
    <!-- PushAlert Unified Code -->
    <script type="text/javascript">
        (function(d, t) {{
            var g = d.createElement(t),
            s = d.getElementsByTagName(t)[0];
            g.src = "https://cdn.pushalert.co/unified_602c5217c4c229cd2935ff6e2aa9b750.js";
            s.parentNode.insertBefore(g, s);
        }}(document, "script"));
    </script>
    <!-- End PushAlert Unified Code -->
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

# ------------------------------------------------------------------
# ROUTES DE L'APPLICATION
# ------------------------------------------------------------------
@app.get("/")
def page_index(request: Request, db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db)
):
    clean_email = email.lower().strip()
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        return render_html("Erreur", "<div class='card'><p style='color:var(--danger)'>Cet email est déjà inscrit.</p></div>")
    
    hashed_pwd = pwd_context.hash(password)
    new_user = User(
        full_name=full_name,
        email=clean_email,
        password_hash=hashed_pwd,
        xbet_id=xbet_id.strip(),
        is_vip=False,
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    response = RedirectResponse(url="/pending", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="session", value=serializer.dumps(new_user.id), httponly=True)
    return response

@app.get("/login")
def page_login(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
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
    db: Session = Depends(get_db)
):
    clean_email = email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user or not pwd_context.verify(password, user.password_hash):
        return render_html("Erreur", "<div class='card'><p style='color:var(--danger)'>Identifiants invalides.</p></div>")
    
    dest = "/admin" if user.is_admin else ("/vip" if user.is_vip else "/pending")
    response = RedirectResponse(url=dest, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="session", value=serializer.dumps(user.id), httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session")
    return response

@app.get("/pending")
def page_pending(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
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
def page_vip(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    if not user["is_vip"] and not user["is_admin"]:
        return RedirectResponse(url="/pending")
    
    bets = db.query(Bet).order_by(Bet.created_at.desc()).all()
    
    bets_html = ""
    for b in bets:
        badge_status = '<span class="badge badge-pending">EN COURS</span>'
        if b.status == "WON":
            badge_status = '<span class="badge badge-won">GAGNÉ</span>'
        elif b.status == "LOST":
            badge_status = '<span class="badge badge-lost">PERDU</span>'
            
        img_html = f'<img src="{b.image_url}" class="bet-img">' if b.image_url else ""
        analysis_html = f'<div class="analysis-box"><strong>Analyse complète :</strong><br>{b.analysis}</div>' if b.analysis else ""
        
        bets_html += f"""
        <div class="card bet-card">
            <div class="bet-header">
                <div>
                    <span style="color:var(--muted); font-size:0.85rem;">{b.league}</span>
                    <h2 style="font-size:1.3rem;">{b.match_title}</h2>
                </div>
                <div>
                    <span class="badge badge-odds">Côte: {b.odds}</span>
                    {badge_status}
                </div>
            </div>
            <p style="margin-bottom:0.5rem;"><strong>Pronostic :</strong> <span style="color:var(--green); font-weight:bold;">{b.bet_type}</span> | <strong>Confiance :</strong> {b.confidence}</p>
            {analysis_html}
            {img_html}
        </div>"""
    
    if not bets_html:
        bets_html = "<div class='card'><p style='text-align:center; color:var(--muted)'>Aucun pronostic disponible pour le moment.</p></div>"

    content = f"<h1 style='margin-bottom:1.5rem;'>Espace VIP 🔒</h1>{bets_html}"
    return render_html("Espace VIP", content, user)

@app.get("/admin")
def page_admin(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user["is_admin"]:
        return RedirectResponse(url="/login")
    
    users = db.query(User).filter(User.is_admin == False).order_by(User.created_at.desc()).all()
    bets = db.query(Bet).order_by(Bet.created_at.desc()).all()
    
    users_rows = ""
    for u in users:
        status_badge = '<span class="badge badge-won">VIP</span>' if u.is_vip else '<span class="badge badge-lost">En attente</span>'
        val_btn = f'<form action="/admin/users/{u.id}/validate" method="POST" style="display:inline;"><button class="btn btn-primary" style="padding:0.3rem 0.6rem; font-size:0.75rem;">Valider VIP</button></form>' if not u.is_vip else ""
        
        users_rows += f"""
        <tr>
            <td>{u.full_name}</td>
            <td>{u.email}</td>
            <td><strong>{u.xbet_id}</strong></td>
            <td>{status_badge}</td>
            <td>
                {val_btn}
                <form action="/admin/users/{u.id}/delete" method="POST" style="display:inline;">
                    <button class="btn btn-danger" style="padding:0.3rem 0.6rem; font-size:0.75rem;">Supprimer</button>
                </form>
            </td>
        </tr>"""

    bets_rows = ""
    for b in bets:
        bets_rows += f"""
        <tr>
            <td>{b.match_title}</td>
            <td>{b.bet_type}</td>
            <td>{b.odds}</td>
            <td><strong>{b.status}</strong></td>
            <td>
                <form action="/admin/bets/{b.id}/status" method="POST" style="display:inline;"><input type="hidden" name="status_val" value="WON"><button class="btn btn-primary" style="padding:0.3rem 0.5rem; font-size:0.7rem;">Gagné</button></form>
                <form action="/admin/bets/{b.id}/status" method="POST" style="display:inline;"><input type="hidden" name="status_val" value="LOST"><button class="btn btn-danger" style="padding:0.3rem 0.5rem; font-size:0.7rem;">Perdu</button></form>
                <form action="/admin/bets/{b.id}/delete" method="POST" style="display:inline;"><button class="btn btn-danger" style="padding:0.3rem 0.5rem; font-size:0.7rem;">Supprimer</button></form>
            </td>
        </tr>"""

    clear_history_btn = """
    <form action="/admin/bets/clear-all" method="POST" onsubmit="return confirm('Attention: Voulez-vous vraiment effacer tout l\\'historique des paris ?');" style="margin-top:1rem;">
        <button class="btn btn-danger" style="width:auto; padding:0.6rem 1rem;">Effacer tout l'historique des paris</button>
    </form>
    """ if bets else ""

    content = f"""
    <h1 style="margin-bottom:1.5rem;">Panneau Administration</h1>
    
    <div class="card">
        <h2 style="color:var(--gold); margin-bottom:1rem;">Publier un nouveau pronostic</h2>
        <form id="betForm" action="/admin/bets/create" method="POST">
            <input type="hidden" id="b64Image" name="b64_image" value="">
            <div class="grid-2">
                <div class="form-group"><label>Match (ex: Real Madrid vs FC Barcelone)</label><input type="text" name="match_title" required></div>
                <div class="form-group"><label>Ligue / Compétition</label><input type="text" name="league" placeholder="ex: LaLiga" required></div>
            </div>
            <div class="grid-2">
                <div class="form-group"><label>Option de pari (ex: Victoire Real Madrid)</label><input type="text" name="bet_type" required></div>
                <div class="form-group"><label>Côte (ex: 1.85)</label><input type="text" name="odds" placeholder="1.85" required></div>
            </div>
            <div class="grid-2">
                <div class="form-group"><label>Indice de confiance (ex: 9/10)</label><input type="text" name="confidence" required></div>
                <div class="form-group"><label>Capture / Image Coupon (Galerie)</label><input type="file" id="filePicker" accept="image/*"></div>
            </div>
            <div class="form-group">
                <label>Analyse détaillée du match</label>
                <textarea name="analysis" rows="5" placeholder="Écris ton analyse ici..."></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Publier le pronostic</button>
        </form>
    </div>

    <script>
        document.getElementById('filePicker').addEventListener('change', function(e) {{
            const file = e.target.files[0];
            if (file) {{
                const reader = new FileReader();
                reader.onload = function(evt) {{
                    document.getElementById('b64Image').value = evt.target.result;
                }};
                reader.readAsDataURL(file);
            }}
        }});
    </script>

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
        <h2 style="margin-bottom:1rem;">Gestion de l'historique des paris</h2>
        <div style="overflow-x:auto;">
            <table>
                <thead><tr><th>Match</th><th>Pari</th><th>Côte</th><th>Statut</th><th>Actions</th></tr></thead>
                <tbody>{bets_rows if bets_rows else '<tr><td colspan="5">Aucun pari publié pour le moment.</td></tr>'}</tbody>
            </table>
        </div>
        {clear_history_btn}
    </div>"""
    return render_html("Administration", content, user)

# ------------------------------------------------------------------
# ACTIONS ADMINISTRATEUR
# ------------------------------------------------------------------
@app.post("/admin/users/{user_id}/validate")
def validate_vip(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.is_vip = True
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/users/{user_id}/delete")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    
    target_user = db.query(User).filter(User.id == user_id, User.is_admin == False).first()
    if target_user:
        db.delete(target_user)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/create")
def create_bet(
    request: Request,
    match_title: str = Form(...),
    league: str = Form(...),
    bet_type: str = Form(...),
    odds: str = Form(...),
    confidence: str = Form(...),
    analysis: str = Form(""),
    b64_image: Optional[str] = Form(""),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403)

    clean_odds_str = odds.replace(",", ".").strip()
    try:
        clean_odds = float(clean_odds_str)
    except ValueError:
        clean_odds = 1.0

    image_url = b64_image.strip() if b64_image and len(b64_image.strip()) > 0 else None

    new_bet = Bet(
        match_title=match_title,
        league=league,
        bet_type=bet_type,
        odds=clean_odds,
        confidence=confidence,
        analysis=analysis,
        image_url=image_url
    )
    db.add(new_bet)
    db.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/{bet_id}/status")
def update_bet_status(bet_id: int, request: Request, status_val: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    
    bet = db.query(Bet).filter(Bet.id == bet_id).first()
    if bet:
        bet.status = status_val
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/{bet_id}/delete")
def delete_bet(bet_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    
    bet = db.query(Bet).filter(Bet.id == bet_id).first()
    if bet:
        db.delete(bet)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/bets/clear-all")
def clear_all_bets(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user["is_admin"]: raise HTTPException(status_code=403)
    
    db.query(Bet).delete()
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
