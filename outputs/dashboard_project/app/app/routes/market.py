# from fastapi import APIRouter, Request
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates

# router = APIRouter()
# templates = Jinja2Templates(directory="app/templates")

# @router.get("/market", response_class=HTMLResponse)
# async def market_page(request: Request, tipo: str = "impo"):
#     return templates.TemplateResponse("market.html", {
#         "request": request,
#         "tipo": tipo
#     })
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
#templates = Jinja2Templates(directory="app/templates")  # ajuste se necessário
templates = Jinja2Templates(directory="templates")

@router.get("/market", response_class=HTMLResponse)
async def market_page(request: Request, tipo: str = "expo"):
    ano_atual = datetime.now().year
    ano_selecionado = ano_atual  # ou outro valor se for dinâmico

    return templates.TemplateResponse("market.html", {
        "request": request,
        "ano_atual": ano_atual,
        "ano_selecionado": ano_selecionado,
        "tipo": tipo
    })
