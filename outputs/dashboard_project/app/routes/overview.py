from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.db.database import (
    engine, 
    get_ano_mes_max, 
    get_dados_volume_preco,
    get_dados_evolucao_mensal, 
    get_kpis_resumo, 
    get_distribuicao_volume
)
from app.utils.plotly_utils import (
    grafico_historico_volume_preco, 
    grafico_evolucao_mensal, 
    grafico_distribuicao_volume
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/overview", response_class=HTMLResponse)
async def overview_page(
    request: Request,
    tipo: str = "impo",
    ano: int | None = None,
    filtro: str = "uf"           # 👈 novo parâmetro de filtro, default 'uf'
):
    nome_tabela = f"pescados_dados_{tipo}"
    ano_atual, mes_max_oficial = get_ano_mes_max(nome_tabela)
    ano_selecionado = ano or ano_atual

    # Ajusta mes_max para anos anteriores
    if ano_selecionado < ano_atual:
        mes_max_oficial = 12

    # KPIs
    kpis = get_kpis_resumo(engine, tipo, ano_selecionado)

    # Gráficos principais
    df_hist = get_dados_volume_preco(engine, tipo, ano_selecionado)
    grafico = grafico_historico_volume_preco(df_hist, tipo)

    df_mensal = get_dados_evolucao_mensal(engine, tipo, ano_selecionado)
    grafico_acumulado = grafico_evolucao_mensal(df_mensal)

    # Gráfico 3 (donut): distribuição por filtro selecionado
    # donut (N O V O)
    filtro_options = {
        "paises":   "País",
        "uf":       "UF",
        "ncm":      "NCM",
        "especie":  "Espécie",
        "categoria":"Categoria",
    }
    label = filtro_options.get(filtro, "País")

    df_dist = get_distribuicao_volume(engine, tipo, ano_selecionado, filtro)
    grafico_donut = grafico_distribuicao_volume(df_dist, label=label, top_n=20)




    return templates.TemplateResponse("overview.html", {
        "request": request,
        "tipo": tipo,
        "ano_atual": ano_atual,
        "ano_selecionado": ano_selecionado,
        "mes_max": mes_max_oficial,

        # KPIs
        "kpi_volume": kpis["kpi_volume"],            # toneladas
        "kpi_valor":  kpis["kpi_valor"],        # milhões USD
        "kpi_preco":  kpis["kpi_preco"],         # USD/ton
        "kpi_volume_delta": kpis["kpi_volume_delta"],
        "kpi_valor_delta":  kpis["kpi_valor_delta"],
        "kpi_preco_delta":  kpis["kpi_preco_delta"],

        # gráficos
        "grafico": grafico,
        "grafico_acumulado": grafico_acumulado,

        # Seletor e donut
        "filtro_options": filtro_options,   # <- NECESSÁRIO
        "filtro": filtro,                   # <- NECESSÁRIO (para marcar selected)
        "grafico_distribuicao": grafico_donut,
    })
