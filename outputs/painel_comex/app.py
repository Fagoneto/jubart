from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import overview, market, ncm

app = FastAPI()

# Rotas
app.include_router(overview.router)
app.include_router(market.router)
app.include_router(ncm.router)

# Static (CSS, Imagens etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Página inicial redireciona para overview
@app.get("/")
def redirect_root():
    return {"message": "Acesse /overview para visualizar o painel."}
