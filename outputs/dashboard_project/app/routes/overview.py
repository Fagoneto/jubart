from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils.plotly_utils import grafico_historico_volume_preco, grafico_evolucao_mensal
from app.db.database import engine, get_ano_mes_max, get_dados_volume_preco, get_dados_evolucao_mensal 

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/overview", response_class=HTMLResponse)
async def overview_page(request: Request, tipo: str = "impo", ano: int = None):
    nome_tabela = f"pescados_dados_{tipo}"
    ano_atual, mes_max = get_ano_mes_max(nome_tabela)
    ano_selecionado = ano if ano else ano_atual

    df = get_dados_volume_preco(engine, tipo, ano_selecionado)
    grafico = grafico_historico_volume_preco(df, tipo)
    
    df_mensal = get_dados_evolucao_mensal(engine, tipo, ano_selecionado)
    grafico_acumulado = grafico_evolucao_mensal(df_mensal)

    return templates.TemplateResponse("overview.html", {
        "request": request,
        "grafico": grafico,
        "tipo": tipo,
        "ano_atual": ano_atual,
        "mes_max": mes_max,
        "ano_selecionado": ano_selecionado,
        "grafico_acumulado": grafico_acumulado

    })


