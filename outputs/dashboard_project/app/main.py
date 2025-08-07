from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.routes import overview, market

app = FastAPI()

# Arquivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Rotas
app.include_router(overview.router)
app.include_router(market.router)

# Redirecionamento padrão
@app.get("/")
async def root():
    return RedirectResponse(url="/overview")
