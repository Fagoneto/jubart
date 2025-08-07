from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routes.overview import router as overview_router


app = FastAPI()

app.include_router(overview_router)

@app.get("/")
async def root():
    return {"message": "Acesse /overview para o painel principal"}



# Montar rotas de templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir os módulos
app.include_router(overview_router, prefix="/overview", tags=["Overview"])

# Redirecionamento da raiz para overview (opcional)
@app.get("/")
async def root_redirect():
    return {"message": "Acesse /overview para o painel principal"}
