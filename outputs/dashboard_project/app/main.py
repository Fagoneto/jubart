from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# IMPORTS DAS ROTAS
# Se sua app estiver estruturada como .../app/main.py e .../app/routes/*.py
# use a linha abaixo:
from routes import overview, market
# Se der erro de import, troque por:
# from routes import overview, market

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

# ===== STATIC =====
# Como main.py está dentro de app/, a pasta estática é "static" (irmã de main.py).
app.mount("/static", StaticFiles(directory="static"), name="static")
# Arquivos estáticos
#app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ===== ROTAS =====
app.include_router(overview.router)
app.include_router(market.router)

# ===== HEALTHCHECK =====
@app.get("/health", tags=["health"])
def health():
    return {"ok": True}

# ===== ROOT REDIRECT =====
@app.get("/")
async def root():
    return RedirectResponse(url="/overview")
