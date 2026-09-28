import os
import json
import pickle
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Form, Query, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from rag_faiss import build_domain_index, search_domain, DOMAINS
from llm import generate_with_phi3
from auth import hash_password, verify_password, create_access_token, verify_token
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------
# FastAPI Setup
# ---------------------------------------------------------
app = FastAPI(title="Federated RAG Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# STATIC & TEMPLATE FOLDERS
# ---------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------------
# Admin Authentication
# ---------------------------------------------------------
def verify_admin(username: str = Query(...), password: str = Query(...)):
    if username != "admin" or password != "admin123":
        raise HTTPException(status_code=401, detail="Admin authentication failed")
    return True


@app.get("/admin/users")
def list_users(username: str = Query(...), password: str = Query(...)):
    verify_admin(username, password)
    users = load_users()
    return users


@app.get("/admin/user_data/{user}")
def get_user_data(user: str, username: str = Query(...), password: str = Query(...)):
    verify_admin(username, password)
    users = load_users()
    return users.get(user, {})


@app.post("/admin/rebuild_index")
def admin_rebuild_index(domain: str, username: str = Query(...), password: str = Query(...)):
    verify_admin(username, password)
    if domain not in DOMAINS:
        raise HTTPException(status_code=400, detail="Unknown domain")
    chunks = build_domain_index(domain)
    return {"domain": domain, "chunks_indexed": chunks}


# ✅ NEW — System Statistics
@app.get("/admin/system_stats")
def get_system_stats(username: str = Query(...), password: str = Query(...)):
    verify_admin(username, password)

    users = load_users()
    total_users = len(users)

    today = datetime.now().date()
    active_today = 0

    for user_data in users.values():
        last_login = user_data.get("last_login")
        if last_login:
            try:
                last_login_date = datetime.fromisoformat(last_login).date()
                if last_login_date == today:
                    active_today += 1
            except Exception:
                pass

    return {"total_users": total_users, "active_today": active_today}


# ✅ NEW — Rebuild all indexes
@app.post("/admin/rebuild_all_indexes")
def admin_rebuild_all_indexes(username: str = Query(...), password: str = Query(...)):
    verify_admin(username, password)
    results = {}

    for domain in DOMAINS:
        try:
            chunks = build_domain_index(domain)
            results[domain] = {"chunks_indexed": chunks}
        except Exception as e:
            results[domain] = {"error": str(e)}

    return {"status": "completed", "results": results}


# ---------------------------------------------------------
# Serve Frontend
# ---------------------------------------------------------
@app.get("/")
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ---------------------------------------------------------
# File paths
# ---------------------------------------------------------
USERS_FILE = r"C:\Users\dhars\OneDrive\Attachments\Desktop\federated_chatbot\federated_chatbot\backend\users.json"
BASE_USER_DIR = r"C:\Users\dhars\OneDrive\Attachments\Desktop\federated_chatbot\federated_chatbot\backend\users_data"

# ---------------------------------------------------------
# User Data Load/Save
# ---------------------------------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ---------------------------------------------------------
# Auth (OAuth2 token system)
# ---------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    username = verify_token(token)
    users = load_users()
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

# ---------------------------------------------------------
# Personas
# ---------------------------------------------------------
PERSONAS = {
    "fitness": "You are an energetic fitness coach. Answer concisely.",
    "mental": "You are a calm mental wellness mentor. Answer concisely.",
    "academic": "You are a precise academic assistant. Answer concisely."
}

# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------
class BuildRequest(BaseModel):
    domain: str


class ChatRequest(BaseModel):
    bot: str
    question: str

# ---------------------------------------------------------
# Federated-style local embeddings
# ---------------------------------------------------------
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def ensure_user_dir(username: str):
    path = os.path.join(BASE_USER_DIR, username)
    os.makedirs(path, exist_ok=True)
    return path


def save_user_chat_embedding(username: str, text: str):
    user_dir = ensure_user_dir(username)
    file_path = os.path.join(user_dir, "chat_embeddings.pkl")

    embedding = embedder.encode([text], convert_to_numpy=True)

    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = pickle.load(f)
    else:
        data = []

    data.append(embedding[0])

    with open(file_path, "wb") as f:
        pickle.dump(data, f)


# ---------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------
@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    users = load_users()

    if username in users:
        raise HTTPException(status_code=400, detail="User already exists")

    users[username] = {
        "hashed_password": hash_password(password),
        "preferences": {}
    }

    save_users(users)
    return {"msg": "Registered successfully"}


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    users = load_users()

    user = users.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ✅ Update last login for system stats
    users[username]["last_login"] = datetime.now().isoformat()
    save_users(users)

    token = create_access_token({"sub": username})
    return {"access_token": token, "token_type": "bearer", "username": username}


# ---------------------------------------------------------
# RAG Routes
# ---------------------------------------------------------
@app.post("/build_index")
def build_index(req: BuildRequest, username: str = Depends(get_current_user)):
    if req.domain not in DOMAINS:
        raise HTTPException(status_code=400, detail="Unknown domain")

    chunks = build_domain_index(req.domain)
    return {"domain": req.domain, "chunks_indexed": chunks}


@app.get("/chat/history/{bot}")
def get_chat_history_endpoint(
    bot: str,
    username: str = Depends(get_current_user)
):
    if bot not in DOMAINS:
        raise HTTPException(status_code=400, detail="Unknown bot")

    # For now return empty array since chat history saving isn't implemented
    return {"bot": bot, "history": []}


@app.post("/multi_rag_chat")
def multi_rag_chat(req: ChatRequest, username: str = Depends(get_current_user)):
    save_user_chat_embedding(username, req.question)

    bot = req.bot.lower()
    if bot not in DOMAINS:
        raise HTTPException(status_code=400, detail="Unknown bot")

    docs = search_domain(req.question, bot, top_k=3)

    if docs:
        context = "\n\n".join(docs)
        prompt = (
            f"{PERSONAS[bot]}\n\nContext:\n{context}\n\n"
            f"Question: {req.question}\nAnswer concisely."
        )
    else:
        prompt = (
            f"{PERSONAS[bot]}\n\n"
            f"Question: {req.question}\n"
            f"Answer concisely."
        )

    answer = generate_with_phi3(prompt)

    return {
        "bot": bot,
        "response": answer,
        "context_used": docs
    }
