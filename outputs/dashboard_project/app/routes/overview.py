from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from db.database import (
    engine, 
    get_ano_mes_max, 
    get_dados_volume_preco,
    get_dados_evolucao_mensal, 
    get_kpis_resumo, 
    get_distribuicao_volume
)
from utils.plotly_utils import (
    grafico_historico_volume_preco, 
    grafico_evolucao_mensal, 
    grafico_distribuicao_volume
)

router = APIRouter()
#templates = Jinja2Templates(directory="app/templates")
templates = Jinja2Templates(directory="templates")

# @router.get("/overview", response_class=HTMLResponse)
# async def overview_page(
#     request: Request,
#     tipo: str = "impo",
#     ano: int | None = None,
#     filtro: str = "uf"           # 👈 novo parâmetro de filtro, default 'uf'
# ):
#     nome_tabela = f"pescados_dados_{tipo}"
#     ano_atual, mes_max_oficial = get_ano_mes_max(nome_tabela)
#     ano_selecionado = ano or ano_atual

#     # Ajusta mes_max para anos anteriores
#     if ano_selecionado < ano_atual:
#         mes_max_oficial = 12

#     # KPIs
#     kpis = get_kpis_resumo(engine, tipo, ano_selecionado)

#     # Gráficos principais
#     df_hist = get_dados_volume_preco(engine, tipo, ano_selecionado)
#     grafico = grafico_historico_volume_preco(df_hist, tipo)

#     df_mensal = get_dados_evolucao_mensal(engine, tipo, ano_selecionado)
#     grafico_acumulado = grafico_evolucao_mensal(df_mensal)

#     # Gráfico 3 (donut): distribuição por filtro selecionado
#     # donut (N O V O)
#     filtro_options = {
#         "paises":   "País",
#         "uf":       "UF",
#         "ncm":      "NCM",
#         "especie":  "Espécie",
#         "categoria":"Categoria",
#     }
#     label = filtro_options.get(filtro, "País")

#     df_dist = get_distribuicao_volume(engine, tipo, ano_selecionado, filtro)
#     grafico_donut = grafico_distribuicao_volume(df_dist, label=label, top_n=20)




#     return templates.TemplateResponse("overview.html", {
#         "request": request,
#         "tipo": tipo,
#         "ano_atual": ano_atual,
#         "ano_selecionado": ano_selecionado,
#         "mes_max": mes_max_oficial,

#         # KPIs
#         "kpi_volume": kpis["kpi_volume"],            # toneladas
#         "kpi_valor":  kpis["kpi_valor"],        # milhões USD
#         "kpi_preco":  kpis["kpi_preco"],         # USD/ton
#         "kpi_volume_delta": kpis["kpi_volume_delta"],
#         "kpi_valor_delta":  kpis["kpi_valor_delta"],
#         "kpi_preco_delta":  kpis["kpi_preco_delta"],

#         # gráficos
#         "grafico": grafico,
#         "grafico_acumulado": grafico_acumulado,

#         # Seletor e donut
#         "filtro_options": filtro_options,   # <- NECESSÁRIO
#         "filtro": filtro,                   # <- NECESSÁRIO (para marcar selected)
#         "grafico_distribuicao": grafico_donut,
#     })
@router.head("/overview")
async def overview_head(tipo: str = "impo", ano: int | None = None, filtro: str = "uf"):
    nome_tabela = f"pescados_dados_{tipo}"
    ano_atual, mes_max_oficial = get_ano_mes_max(nome_tabela)
    ano_selecionado = ano or ano_atual
    if ano_selecionado < ano_atual:
        mes_max_oficial = 12
    version = f"{tipo}:{int(ano_selecionado):04d}:{int(mes_max_oficial):02d}:{filtro}"
    return Response(
        status_code=200,
        headers={
            "ETag": version,
            "Cache-Control": "public, max-age=2592000, must-revalidate",
        },
    )

@router.get("/overview", response_class=HTMLResponse)
async def overview_page(
    request: Request,
    tipo: str = "impo",
    ano: int | None = None,
    filtro: str = "uf",
):
    nome_tabela = f"pescados_dados_{tipo}"
    # já com seu padrão
    ano_atual, mes_max_oficial = get_ano_mes_max(nome_tabela)
    ano_selecionado = ano or ano_atual
    if ano_selecionado < ano_atual:
        mes_max_oficial = 12

    # ---------- ETag (versão mensal por tipo/ano/filtro) ----------
    # versão do cache
    version = f"{tipo}:{int(ano_selecionado):04d}:{int(mes_max_oficial):02d}:{filtro}"

    client_etag = request.headers.get("if-none-match")
    if client_etag == version:
        # Já tem a mesma versão → 304 sem corpo
        return Response(
            status_code=304,
            headers={
                "ETag": version,
                "Cache-Control": "public, max-age=2592000, must-revalidate",  # ~30 dias
            },
        )

    # ---------- Dados e gráficos (sua lógica atual, intacta) ----------
    kpis = get_kpis_resumo(engine, tipo, ano_selecionado)

    df_hist = get_dados_volume_preco(engine, tipo, ano_selecionado)
    grafico = grafico_historico_volume_preco(df_hist, tipo)

    df_mensal = get_dados_evolucao_mensal(engine, tipo, ano_selecionado)
    grafico_acumulado = grafico_evolucao_mensal(df_mensal)

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

    resp = templates.TemplateResponse("overview.html", {
        "request": request,
        "tipo": tipo,
        "ano_atual": ano_atual,
        "ano_selecionado": ano_selecionado,
        "mes_max": mes_max_oficial,

        # KPIs
        "kpi_volume": kpis["kpi_volume"],
        "kpi_valor":  kpis["kpi_valor"],
        "kpi_preco":  kpis["kpi_preco"],
        "kpi_volume_delta": kpis["kpi_volume_delta"],
        "kpi_valor_delta":  kpis["kpi_valor_delta"],
        "kpi_preco_delta":  kpis["kpi_preco_delta"],

        # Gráficos
        "grafico": grafico,
        "grafico_acumulado": grafico_acumulado,

        # Donut
        "filtro_options": filtro_options,
        "filtro": filtro,
        "grafico_distribuicao": grafico_donut,
    })

    # Cabeçalhos de cache: mesmo HTML é reutilizado até mudar a versão
    resp.headers["ETag"] = version
    resp.headers["Cache-Control"] = "public, max-age=2592000, must-revalidate"
    return resp
