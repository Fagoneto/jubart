# app/main.py
from datetime import datetime
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# from app.routes import overview, market, pages
# from app.db.database import engine

from .routes import overview, market, pages
from .db.database import engine

# ---- Build tag para verificarmos a versão em produção
BUILD_TAG = os.getenv("BUILD_TAG", datetime.utcnow().strftime("dev-%Y%m%d-%H%M"))

# ---- UMA ÚNICA INSTÂNCIA DA APP
app = FastAPI(
    title="Jubart Dashboard Project",
    version=BUILD_TAG,  # aparece no /docs também
)

# ---- ROTA DE VERSÃO
@app.get("/__version__")
def version():
    return {"build": BUILD_TAG}

# ---- CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # restrinja depois se quiser
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- STATIC
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---- ROTAS (APIRouter)
app.include_router(overview.router)
app.include_router(market.router)
app.include_router(pages.router)

# ---- HEALTHCHECKS
@app.get("/health", tags=["health"])
def health():
    return {"ok": True}

@app.get("/health/dbinfo", tags=["health"])
def dbinfo():
    url = str(engine.url)
    if engine.url.password:
        url = url.replace(engine.url.password, "***")
    return {"dialect": engine.url.get_backend_name(), "url": url}

@app.get("/health/maxperiod", tags=["health"])
def health_maxperiod():
    sql = text("""
        SELECT ano, mes
        FROM pescados_dados_impo
        ORDER BY ano DESC, mes DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql).one()
    return JSONResponse({"ano": int(row.ano), "mes": int(row.mes)})

# ---- MIDDLEWARE: segurança + no-cache em rotas dinâmicas
NO_CACHE_PREFIXES = ("/overview", "/market", "/api", "/paineis", "/graficos")

@app.middleware("http")
async def security_and_cache_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = (
        "frame-ancestors https://jubartdata.com.br https://www.jubartdata.com.br;"
    )
    if request.url.path.startswith(NO_CACHE_PREFIXES):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

# ---- ROOT REDIRECT
@app.get("/")
async def root():
    return RedirectResponse(url="/overview")
