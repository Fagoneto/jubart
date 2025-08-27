from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pathlib
from fastapi.staticfiles import StaticFiles

from app.routes import overview, market, pages
from app.db.database import engine

# IMPORTS DAS ROTAS
# Se sua app estiver estruturada como .../app/main.py e .../app/routes/*.py
# use a linha abaixo:
# from routes import overview, market
# from routes import pages
# Se der erro de import, troque por:
# from routes import overview, market

from app.db.database import engine

app = FastAPI(
    title="Jubart Dashboard Project",
    version="1.0.0"
)

# ===== CORS =====
# Libere tudo por enquanto; depois você pode restringir para seus domínios:
# ex.: ["https://jubartdata.com.br", "https://jubart.github.io"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # <-- restrinja depois, se desejar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = pathlib.Path(__file__).resolve().parent  # = app/
STATIC_DIR = BASE_DIR / "static"
# ===== STATIC =====
# Como main.py está dentro de app/, a pasta estática é "static" (irmã de main.py).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Arquivos estáticos
#app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ===== ROTAS =====
app.include_router(overview.router)
app.include_router(market.router)
app.include_router(pages.router)

# ===== HEALTHCHECK =====
@app.get("/health", tags=["health"])
def health():
    return {"ok": True}

# ===== ROOT REDIRECT =====
@app.get("/")
async def root():
    return RedirectResponse(url="/overview")


@app.get("/health/dbinfo")
def dbinfo():
    url = str(engine.url)
    # oculta a senha
    if engine.url.password:
        url = url.replace(engine.url.password, "***")
    return {"dialect": engine.url.get_backend_name(), "url": url}


# @app.middleware("http")
# async def security_and_cache_headers(request: Request, call_next):
#     resp = await call_next(request)
#     # Permitir incorporação apenas pelo seu domínio (se usar <iframe> interno)
#     resp.headers["Content-Security-Policy"] = (
#         "frame-ancestors https://jubartdata.com.br https://www.jubartdata.com.br;"
#     )
#     # Evitar cache agressivo enquanto testamos atualização de dados
#     resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
#     resp.headers["Pragma"] = "no-cache"
#     resp.headers["Expires"] = "0"
#     return resp

# ===== MIDDLEWARE: Segurança + No-Cache p/ rotas dinâmicas =====
NO_CACHE_PREFIXES = ("/overview", "/market", "/api", "/paineis", "/graficos")

@app.middleware("http")
async def security_and_cache_headers(request: Request, call_next):
    resp = await call_next(request)

    # Segurança para iframes
    resp.headers["Content-Security-Policy"] = (
        "frame-ancestors https://jubartdata.com.br https://www.jubartdata.com.br;"
    )

    # No-cache somente para rotas dinâmicas (HTML/JSON gerado)
    if request.url.path.startswith(NO_CACHE_PREFIXES):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"

    return resp


# em app/main.py (ou num router de health)
from sqlalchemy import text
from fastapi.responses import JSONResponse
from app.db.database import engine

@app.get("/health/maxperiod")
def health_maxperiod():
    sql = text("""
        SELECT ano, mes
        FROM pescados_dados_impo   -- ajuste o nome da tabela
        ORDER BY ano DESC, mes DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql).one()
    return JSONResponse({"ano": int(row.ano), "mes": int(row.mes)})
