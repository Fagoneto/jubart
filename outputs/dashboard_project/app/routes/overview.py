from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils.plotly_utils import gerar_grafico_plotly
from app.db.database import get_dados_anuais_com_mes_corrente

from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/overview", response_class=HTMLResponse)
async def overview_page(request: Request, tipo: str = "impo"):
    template_path = Path("app/templates/overview.html")
    print("🧩 Caminho do template que estou editando:", template_path.resolve())
    print("🧩 Existe?", template_path.exists())

    df, ano_atual, mes_max = get_dados_anuais_com_mes_corrente(tipo)

    print("📊 Tipo:", tipo)
    print("📅 Ano atual:", ano_atual)
    print("📅 Mês max:", mes_max)
    print("📈 DataFrame:")
    print(df.head())

    if df.empty:
        print("⚠️ DataFrame vazio!")
        tabela_html = "<p style='color:red;'>🚫 Nenhum dado encontrado para essa operação.</p>"
        grafico = ""
    else:
        print("✅ Dados prontos para exibição.")
        tabela_html = df.to_html(index=False, classes="tabela-sql")
        grafico = gerar_grafico_plotly(df)

    template_path = Path("app/templates/overview.html")
    print("📁 TEMPLATE USADO:", template_path.resolve())  # 👈 Mostra caminho exato

    print("🔧 Conteúdo do gráfico:", grafico[:100])  # Mostra os primeiros 100 caracteres
    print("🔧 Conteúdo da tabela:", tabela_html[:100])


    return templates.TemplateResponse("overview.html", {
        "request": request,
        "grafico": grafico,
        "tipo": tipo,
        "ano_atual": ano_atual,
        "mes_max": mes_max,
        "tabela": tabela_html
    })
