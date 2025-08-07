from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from db import get_dados_anuais_com_mes_corrente, gerar_grafico_integrado_por_filtro
import plotly.io as pio

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/market")
async def market_view(request: Request, tipo: str = "impo", filtro: str = "paises", filtro_secundario: str = "uf"):
    # Gráfico de barras
    df_barra, ano_atual, mes_max = get_dados_anuais_com_mes_corrente(tipo)
    if df_barra.empty:
        grafico_barra_html = "<p><strong>Sem dados disponíveis.</strong></p>"
    else:
        fig_barra = px.bar(
            df_barra,
            x="ano",
            y="Volume",
            color="Tipo",
            barmode="group",
            title=f"{tipo.capitalize()}ção — até {mes_max}/{ano_atual}",
            labels={"ano": "Ano", "Volume": "Volume (kg)", "Tipo": "Legenda"}
        )
        fig_barra.update_layout(template="plotly_white")
        grafico_barra_html = pio.to_html(fig_barra, full_html=False)

    # Gráfico combinado
    fig_integrado, _ = gerar_grafico_integrado_por_filtro(tipo, filtro, filtro_secundario)
    grafico_integrado_html = pio.to_html(fig_integrado, full_html=False) if fig_integrado else "<p>Sem dados para gráfico combinado.</p>"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "grafico_html": grafico_barra_html,
        "grafico_pizza_html": grafico_integrado_html,
        "tipo": tipo,
        "pagina": "market",
        "ano_atual": ano_atual,
        "filtro": filtro,
        "filtro_secundario": filtro_secundario,
    })
