from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from db import get_dados_anuais_com_mes_corrente, gerar_grafico_integrado_por_filtro  # etc

router = APIRouter()
templates = Jinja2Templates(directory="templates")



@router.get("/overview", response_class=HTMLResponse)
async def painel_overview(request: Request, tipo: str = "impo", ano: int = 2024, filtro: str = "uf", filtro_secundario: str = "paises"):
    # aqui você usa as funções do db.py
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pagina": "overview",
        "tipo": tipo,
        "ano_atual": ano,
        "filtro": filtro,
        "filtro_secundario": filtro_secundario,
        "volume": "...",
        "valor": "...",
        "preco": "...",
        "var_volume": "...",
        "var_valor": "...",
        "var_preco": "...",
        "cor_volume": "...",
        "cor_valor": "...",
        "cor_preco": "...",
        "grafico_volume": "...",
        "grafico_evolucao": "...",
        "grafico_categoria": "...",
        "grafico_segmento": "...",
        "grafico_quantidade": "...",
    })
