# --- Bibliotecas padrão ---
import os

# --- Bibliotecas de terceiros ---
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dotenv import load_dotenv
from routes import overview, market, ncm

# --- Carregar variáveis de ambiente ---
load_dotenv()

user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
database = os.getenv("database")


# --- Inicialização do app ---
app = FastAPI()

app.include_router(overview.router)
app.include_router(market.router)
app.include_router(ncm.router)

# Montar diretórios estáticos e de templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Exemplo com SQLAlchemy
engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")

# Caminho base dos dados locais (caso não use SQL)
CAMINHO_DADOS = "/Users/franciscoabraao/Documents/Jubart_2025/dados_brutos/dados_comex_pescado_brasil"

def painel_superior(engine, tipo_dado, ano_final):
    with engine.connect() as connection:
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM pescados_dados_{tipo_dado} WHERE ano = {ano_final}")
        ).fetchone()
        mes_max = mes_result[0] if mes_result and mes_result[0] is not None else 12

        # Coletar dados dos dois anos até o mesmo mês
        query = text(f"""
            SELECT 
                ano,
                SUM(kg) AS total_kg,
                SUM(valor) AS total_valor
            FROM pescados_dados_{tipo_dado}
            WHERE 
                ((ano = :ano_atual AND mes <= :mes_max)
                OR
                (ano = :ano_anterior AND mes <= :mes_max))
            GROUP BY ano
            ORDER BY ano
        """)

        df = pd.read_sql_query(query, connection, params={
            "ano_atual":  ano_final,
            "ano_anterior":  ano_final - 1,
            "mes_max": mes_max
        })

    # Calcular preço médio (USD/kg)
    df["preco_medio"] = df["total_valor"] / df["total_kg"]

    # Ajustes de escala
    df["total_kg"] = df["total_kg"] / 1000
    df["total_valor"] = df["total_valor"] / 1000

    # Transpor
    df_transposto = df.set_index("ano").T

    # Renomear os índices antes de adicionar a variação
    df_transposto = df_transposto.rename(index={
        'total_kg': 'Volume (toneladas)',
        'total_valor': 'Valor (USD x 1000)',
        'preco_medio': 'Preço Médio (USD/kg)'
    })

    # Calcular variação (%)
    df_transposto['Variação (%)'] = (
        (df_transposto[ano_final] - df_transposto[ano_final - 1]) /
        df_transposto[ano_final - 1]
    ) * 100

    return df_transposto

def gerar_grafico_volume_por_filtro(engine, tipo_dado, ano_final):
    ano_min = ano_final - 5
    with engine.connect() as connection:
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM pescados_dados_{tipo_dado} WHERE ano = {ano_final}")
        ).fetchone()
        mes_max = mes_result[0] if mes_result and mes_result[0] is not None else 12

        query = text(f"""
            SELECT
                ano,
                SUM(CASE WHEN mes <= {mes_max} THEN kg ELSE 0 END) AS volume_mes_corrente,
                SUM(CASE WHEN mes <= {mes_max} THEN valor ELSE 0 END) AS valor_mes_corrente
            FROM pescados_dados_{tipo_dado}
            WHERE ano BETWEEN {ano_min} AND {ano_final}
            GROUP BY ano
            ORDER BY ano
        """)
        df = pd.read_sql_query(query, con=connection)

    # Calcular preço médio
    df["preco_medio"] = df["valor_mes_corrente"] / df["volume_mes_corrente"]
    df["volume_mes_corrente"] = df["volume_mes_corrente"]  # pode dividir por 1_000_000 se quiser M

    # Criar figura com barras
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["ano"],
        y=df["volume_mes_corrente"],
        name="Volume (kg)",
        marker_color="royalblue"
    ))

    fig.add_trace(go.Scatter(
        x=df["ano"],
        y=df["preco_medio"],
        name="Preço Médio (USD/kg)",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color="red", width=3),
        marker=dict(size=7)
    ))

    fig.update_layout(
        title=f"{'Importações' if tipo_dado == 'impo' else 'Exportações'} - Evolução do Volume e Preço Médio",
        xaxis=dict(title="Ano"),
        yaxis=dict(title="Volume (kg)", showgrid=False),
        yaxis2=dict(
            title="Preço Médio (USD/kg)",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        legend=dict(
            title="",
            orientation="h",
            yanchor="bottom",
            y=-0.3,  # mais abaixo do gráfico
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        bargap=0.2,
        height=400,
        margin=dict(l=20, r=20, t=40, b=40)
    )

    return fig

def gerar_grafico_evolucao_acumulada(engine, tipo_dado, ano_final):
    ano_min = ano_final - 5
    with engine.connect() as connection:
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM pescados_dados_{tipo_dado} WHERE ano = {ano_final}")
        ).fetchone()
        mes_max = mes_result[0] if mes_result and mes_result[0] is not None else 12

        query = text(f"""
            SELECT
                ano,
                mes,
                SUM(kg) AS total_volume
            FROM pescados_dados_{tipo_dado}
            WHERE ano BETWEEN {ano_min} AND {ano_final}
            GROUP BY ano, mes
            ORDER BY ano, mes
        """)

        df_mes_ano = pd.read_sql_query(query, con=connection)

    # Preparar o dataframe
    df = df_mes_ano.copy()
    df.rename(columns={'ano': 'year', 'mes': 'month', 'total_volume': 'volume'}, inplace=True)
    df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
    df['cumulative_volume'] = df.groupby('year')['volume'].cumsum()

    current_year = df['year'].max()
    last_year = current_year - 1

    historical_df = df[df['year'] < current_year]

    fig = px.box(
        historical_df,
        x='month',
        y='cumulative_volume',
        title='Evolução Mensal Acumulada de Volume',
        labels={'cumulative_volume': 'Volume Acumulado (kg)', 'month': 'Mês'},
        color_discrete_sequence=['lightblue']
    )

    df_last_year = df[df['year'] == last_year]
    fig.add_trace(go.Scatter(
        x=df_last_year['month'],
        y=df_last_year['cumulative_volume'],
        mode='lines+markers',
        name=f'{last_year} Acumulado',
        line=dict(color='blue', width=2)
    ))

    df_current_year = df[df['year'] == current_year]
    fig.add_trace(go.Scatter(
        x=df_current_year['month'],
        y=df_current_year['cumulative_volume'],
        mode='lines+markers',
        name=f'{current_year} Acumulado',
        line=dict(color='red', width=3)
    ))

    fig.update_layout(
        autosize=True,
        xaxis_title='Mês',
        yaxis_title='Volume Acumulado (kg)',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        plot_bgcolor='white'
    )
    return fig

def gerar_grafico_por_filtro(engine, tipo_dado, ano_selected, filtro):
    
    with engine.connect() as connection:
        query = text(f"""
            SELECT
                {filtro},
                SUM(kg) AS total_volume
            FROM pescados_dados_{tipo_dado}
            WHERE ano = :ano
            GROUP BY {filtro}
            ORDER BY total_volume DESC
            LIMIT 20
        """)
        df = pd.read_sql_query(query, con=connection, params={"ano": ano_selected})

    # Ordenar do maior para o menor
    df = df.sort_values('total_volume', ascending=False)

    # Separar os 5 maiores
    top5 = df.head(5).copy()

    # Calcular o total dos demais e criar 'Outros_2'
    outros_volume = df.iloc[5:]['total_volume'].sum()
    outros_row = pd.DataFrame({filtro: ['Outros_2'], 'total_volume': [outros_volume]})

    # Juntar os dados com 'Outros_2' ao final
    df_final = pd.concat([top5, outros_row], ignore_index=True)

    # Cores: azul escuro para os top5, azul claro para 'Outros_2'
    cores = ['royalblue'] * 5 + ['lightblue']

    # Criar gráfico horizontal manualmente com go.Bar
    fig = go.Figure(go.Bar(
        x=df_final['total_volume'],
        y=df_final[filtro],
        orientation='h',
        marker=dict(color=cores)
    ))

    # Layout
    fig.update_layout(
        title=f"Volume por {filtro.capitalize()} em {ano_selected}",
        xaxis_title="Volume (kg)",
        yaxis_title=filtro.capitalize(),
        yaxis=dict(autorange='reversed'),  # maior em cima
        height=400,
        template='plotly_white',
        margin=dict(t=40, b=80)
    )


    return fig

def gerar_grafico_distribuicao_hierarquica(engine, tipo_dado, ano_atual, filtro, filtro_secundario):
    """
    Gera gráfico sunburst com dois níveis hierárquicos: filtro → filtro_secundario
    Ex: paises → especie ou categoria → uf
    """

    with engine.connect() as connection:
        query = text(f"""
            SELECT
                {filtro},
                {filtro_secundario},
                SUM(kg) AS volume_total
            FROM pescados_dados_{tipo_dado}
            WHERE ano = {ano_atual}
            GROUP BY {filtro}, {filtro_secundario}
        """)

        df = pd.read_sql_query(query, con=connection)

    # Substitui nulos por nome padrão
    df.fillna("Não informado", inplace=True)

    # Agrupar por filtro primário para somar volumes
    df_grupo = df.groupby(filtro)['volume_total'].sum().sort_values(ascending=False)

    # Identificar os 5 maiores
    top5_filtros = df_grupo.head(5).index.tolist()

    # Adicionar 'Outros_2' à lista
    filtros_final = top5_filtros + ['Outros_2']

    # Substituir os que não estão no top 5 por 'Outros_2'
    df[filtro] = df[filtro].apply(lambda x: x if x in top5_filtros else 'Outros_2')

    # Reagrupar após renomear para somar volumes novamente
    df = df.groupby([filtro, filtro_secundario])['volume_total'].sum().reset_index()

    # Gráfico sunburst
    fig = px.sunburst(
        df,
        path=[filtro, filtro_secundario],
        values='volume_total',
        title=f"Distribuição de Volume - {tipo_dado.upper()} ({ano_atual})<br>{filtro.title()} → {filtro_secundario.title()}",
    )

    fig.update_traces(textinfo='label+percent entry',
                      insidetextorientation='radial',
                      marker=dict(line=dict(width=0.5)),
                      domain=dict(x=[0.05, 0.95], y=[0.05, 0.95])  # reduz em ~10% nas bordas                   
    )
    fig.update_layout(
        margin=dict(t=40, b=10, l=10, r=10),
        uniformtext=dict(minsize=10), #mode='hide'),
        autosize=True,
        #sunburstcolorway=['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78'],  # opcional
    )
    return fig

### Construir evolucao das 5 principais
def gerar_grafico_historico_volume_por_filtro(engine, tipo_dado, filtro, salvar_em=None):
    """
    Gera gráfico de linha com o histórico de volume por item do filtro ao longo dos anos (exceto ano mais recente).

    Parâmetros:
    - engine: conexão SQLAlchemy
    - tipo_dado: 'impo' ou 'expo'
    - filtro: 'uf', 'paises', 'especie' ou 'categoria'
    - salvar_em: caminho HTML opcional para salvar o gráfico
    """

    with engine.connect() as connection:
        # Ano mais recente
        ano_atual = connection.execute(
            text(f"SELECT MAX(ano) FROM pescados_dados_{tipo_dado}")
        ).fetchone()[0]

        # Query: excluir ano atual
        query = text(f"""
            SELECT
                ano,
                {filtro},
                SUM(kg) AS volume_total
            FROM pescados_dados_{tipo_dado}
            WHERE ano < {ano_atual}
            GROUP BY ano, {filtro}
            ORDER BY ano, {filtro}
        """)

        df = pd.read_sql_query(query, con=connection)

    # Gráfico de linha
    fig = px.line(
        df,
        x='ano',
        y='volume_total',
        color=filtro,
        markers=True,
        title=f"Evolução Anual do Volume - {tipo_dado.upper()} por {filtro.upper()} (até {ano_atual - 1})",
        labels={'ano': 'Ano', 'volume_total': 'Volume (kg)', filtro: filtro.title()}
    )

    fig.update_layout(xaxis=dict(dtick=1))

    if salvar_em:
        os.makedirs(os.path.dirname(salvar_em), exist_ok=True)
        fig.write_html(salvar_em, include_plotlyjs='cdn')

    return fig

def gerar_grafico_evolucao_por_filtro(engine, tipo_dado, ano_selected, filtro):
    ano_min = ano_selected - 5
    with engine.connect() as connection:
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM pescados_dados_{tipo_dado} WHERE ano = {ano_selected}")
        ).fetchone()
        mes_max = mes_result[0] if mes_result and mes_result[0] is not None else 12

        query = text(f"""
            SELECT
                {filtro},
                ano,
                SUM(kg) AS total_volume,
                SUM(CASE WHEN mes <= {mes_max} THEN kg ELSE 0 END) AS volume_mes_corrente,
                SUM(CASE WHEN mes <= {mes_max} THEN valor ELSE 0 END) AS valor_mes_corrente
            FROM pescados_dados_{tipo_dado}
            WHERE ano BETWEEN {ano_min} AND {ano_selected}
            GROUP BY {filtro}, ano
            ORDER BY ano
        """)

        df = pd.read_sql_query(query, con=connection)

    # Passo 1: selecionar o total por filtro no ano selecionado
    df_top = (
        df[df['ano'] == ano_selected]
        .groupby(filtro, as_index=False)['volume_mes_corrente']
        .sum()
        .sort_values(by='volume_mes_corrente', ascending=False)
    )

    # Passo 2: pegar os 10 primeiros
    top_10 = df_top[filtro].head(5).tolist()

    # Passo 3: criar nova coluna com nome ajustado
    df[filtro] = df[filtro].apply(lambda x: x if x in top_10 else "Outros_2")

    # Passo 4: agrupar novamente
    df_agrupado = (
        df.groupby([filtro, 'ano'], as_index=False)
        .agg({"volume_mes_corrente": "sum"})
    )

    # Passo 5: ordenar pelo ano mais recente e volume
    df_agrupado = df_agrupado.sort_values(
        by=['ano', 'volume_mes_corrente'],
        ascending=[False, False]
    )

    fig = px.line(
        df_agrupado,
        x="ano",
        y="volume_mes_corrente",
        color=filtro,
        markers=True,
        title=f"Evolução Anual do Volume (até {mes_max}/{ano_selected}) por {filtro.capitalize()}",
        labels={
            "ano": "Ano",
            "volume_mes_corrente": "Volume (kg)",
            filtro: filtro.capitalize()
        }
    )

    fig.update_layout(
        height=450,
        template="plotly_white",
        legend_title=filtro.capitalize()
    )

    return fig



#@app.get("/", response_class=HTMLResponse)

@app.get("/", response_class=HTMLResponse)
def root(request: Request, tipo: str = "impo", ano: int = 2024, filtro: str = "uf", filtro_secundario: str = "paises"):
    return overview(request, tipo, ano, filtro, filtro_secundario)

@app.get("/overview", response_class=HTMLResponse)
def overview(request: Request, tipo: str = "impo", ano: int = 2024, filtro: str = "uf", filtro_secundario: str = "paises"):
    return index(request, tipo)

def index(request: Request, tipo: str = "impo"):
    with engine.connect() as connection:
        ano_result = connection.execute(
            text(f"SELECT MAX(ano) FROM pescados_dados_{tipo}")
        ).fetchone()
        ano_atual = ano_result[0]

    ano_param = request.query_params.get("ano")
    ano_selected = int(ano_param) if ano_param and ano_param.isdigit() else ano_atual
    filtro = request.query_params.get("filtro", "paises")
    filtro_secundario = request.query_params.get("filtro_secundario", "especie")


    def formatar_valor(valor):
        return f"{valor:,.0f}".replace(",", ".")
    
    def format_variacao(valor):
        if pd.isna(valor):
            return "—", "black"
        cor = "green" if valor >= 0 else "red"
        sinal = "+" if valor >= 0 else "-"
        return f"{sinal}{abs(valor):,.1f}%".replace(",", "."), cor

    df_metrica = painel_superior(engine, tipo, int(ano_selected))

    volume = formatar_valor(df_metrica.at["Volume (toneladas)", ano_selected])
    valor = formatar_valor(df_metrica.at["Valor (USD x 1000)", ano_selected])
    preco = f"{df_metrica.at['Preço Médio (USD/kg)', ano_selected]:.3f}"

    # Calcular variação (%)
    var_volume = df_metrica.loc["Volume (toneladas)", "Variação (%)"]
    var_valor = df_metrica.loc["Valor (USD x 1000)", "Variação (%)"]
    var_preco = df_metrica.loc["Preço Médio (USD/kg)", "Variação (%)"]


    var_volume_valor, cor_volume = format_variacao(var_volume)
    var_valor_valor, cor_valor = format_variacao(var_valor)
    var_preco_valor, cor_preco = format_variacao(var_preco)



    html_volume = ""
    html_cum = ""
    html_filtro = ""
    html_sunburst = ""
    fig_evolucao_filtro = ""

    try:
        fig_volume = gerar_grafico_volume_por_filtro(engine, tipo, ano_selected)
        fig_cum = gerar_grafico_evolucao_acumulada(engine, tipo, ano_selected)
        fig_filtro = gerar_grafico_por_filtro(engine, tipo, ano_selected, filtro)
        fig_sunburst = gerar_grafico_distribuicao_hierarquica(engine, tipo, ano_selected, filtro, filtro_secundario)
        fig_evolucao_filtro = gerar_grafico_evolucao_por_filtro(engine, tipo, ano_selected, filtro)

        html_volume = pio.to_html(fig_volume, include_plotlyjs="cdn", full_html=False, default_width="100%", default_height="100%")
        html_cum = pio.to_html(fig_cum, include_plotlyjs=False, full_html=False, default_width="100%", default_height="100%")
        html_filtro = pio.to_html(fig_filtro, include_plotlyjs=False, full_html=False, default_width="100%", default_height="100%")
        html_sunburst = pio.to_html(fig_sunburst, include_plotlyjs=False, full_html=False, default_width="100%", default_height="100%")

        html_evolucao_filtro = pio.to_html(fig_evolucao_filtro, include_plotlyjs=False, full_html=False, default_width="100%", default_height="100%")
        
    except Exception as e:
        html_volume = f"<p>Erro ao gerar gráfico volume: {str(e)}</p>"
        html_cum = f"<p>Erro ao gerar gráfico acumulado: {str(e)}</p>"
        html_filtro = f"<p>Erro ao gerar gráfico de filtro: {str(e)}</p>"
        html_sunburst = f"<p>Erro ao gerar gráfico de distribuição hierárquica: {str(e)}</p>"
        html_evolucao_filtro = f"<p>Erro ao gerar gráfico de distribuição hierárquica: {str(e)}</p>"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "grafico_volume": html_volume,
        "grafico_evolucao": html_cum,
        "grafico_categoria": html_filtro,
        "grafico_segmento": html_sunburst,
        "grafico_quantidade": html_evolucao_filtro,
        "tipo": tipo,
        "ano_atual": ano_atual,
        "ano_selected": ano_selected,
        "filtro": filtro,
        "filtro_secundario": filtro_secundario,
        "volume": volume,
        "valor": valor,
        "preco": preco,
        "var_volume": var_volume_valor,
        "var_valor": var_valor_valor,
        "var_preco": var_preco_valor,
        "cor_volume": cor_volume,
        "cor_valor": cor_valor,
        "cor_preco": cor_preco,
    })


@app.get("/market", response_class=HTMLResponse)
def market(request: Request, tipo: str = "impo"):
    with engine.connect() as connection:
        ano_result = connection.execute(
            text(f"SELECT MAX(ano) FROM pescados_dados_{tipo}")
        ).fetchone()
        ano_atual = ano_result[0]

    ano_param = request.query_params.get("ano")
    ano_selected = int(ano_param) if ano_param and ano_param.isdigit() else ano_atual
    filtro = request.query_params.get("filtro", "paises")
    filtro_secundario = request.query_params.get("filtro_secundario", "categoria")

    def formatar_valor(valor):
        return f"{valor:,.0f}".replace(",", ".")

    def format_variacao(valor):
        if pd.isna(valor):
            return "—", "black"
        cor = "green" if valor >= 0 else "red"
        sinal = "+" if valor >= 0 else "-"
        return f"{sinal}{abs(valor):,.1f}%".replace(",", "."), cor

    # --- Métricas ---
    df_metrica = painel_superior(engine, tipo, ano_selected)
    volume = f"{df_metrica.at['Volume (toneladas)', ano_selected]:,.0f}".replace(",", ".")
    valor = f"{df_metrica.at['Valor (USD x 1000)', ano_selected]:,.0f}".replace(",", ".")
    preco = f"{df_metrica.at['Preço Médio (USD/kg)', ano_selected]:.3f}"

    # --- Variações ---
    var_volume_valor, cor_volume = format_variacao(df_metrica.loc["Volume (toneladas)", "Variação (%)"])
    var_valor_valor, cor_valor = format_variacao(df_metrica.loc["Valor (USD x 1000)", "Variação (%)"])
    var_preco_valor, cor_preco = format_variacao(df_metrica.loc["Preço Médio (USD/kg)", "Variação (%)"])

    # --- Gráficos específicos do Market ---
    fig_top_paises = gerar_grafico_por_filtro(engine, tipo, ano_selected, "paises")
    fig_top_categorias = gerar_grafico_por_filtro(engine, tipo, ano_selected, "categoria")
    fig_sunburst = gerar_grafico_distribuicao_hierarquica(engine, tipo, ano_selected, filtro, filtro_secundario)

    html_top_paises = pio.to_html(fig_top_paises, include_plotlyjs="cdn", full_html=False)
    html_top_categorias = pio.to_html(fig_top_categorias, include_plotlyjs=False, full_html=False)
    html_sunburst = pio.to_html(fig_sunburst, include_plotlyjs=False, full_html=False)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "pagina": "market",
        "grafico_volume": html_top_paises,
        "grafico_evolucao": html_top_categorias,
        "grafico_categoria": html_sunburst,
        "grafico_segmento": "",
        "grafico_quantidade": "",
        "tipo": tipo,
        "ano_atual": ano_atual,
        "ano_selected": ano_selected,
        "filtro": filtro,
        "filtro_secundario": filtro_secundario,
        "volume": volume,
        "valor": valor,
        "preco": preco,
        "var_volume": var_volume_valor,
        "var_valor": var_valor_valor,
        "var_preco": var_preco_valor,
        "cor_volume": cor_volume,
        "cor_valor": cor_valor,
        "cor_preco": cor_preco,
    })

@app.get("/ncm", response_class=HTMLResponse)
def ncm_page(request: Request, tipo: str = "impo", ano: int = 2024, filtro: str = "paises", ncm: str = None):
    with engine.connect() as connection:
        # Ano mais recente
        ano_result = connection.execute(
            text(f"SELECT MAX(ano) FROM pescados_dados_{tipo}")
        ).fetchone()
        ano_max = ano_result[0]

        # Descobrir o mes_max para ano_max
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM pescados_dados_{tipo} WHERE ano = :ano"),
            {"ano": ano_max}
        ).fetchone()
        mes_max = mes_result[0] if mes_result and mes_result[0] is not None else 12

        # Buscar lista de NCMs únicos
        query_ncm = text(f"""
            SELECT DISTINCT ncm
            FROM pescados_dados_{tipo}
            WHERE ano = :ano
            ORDER BY ncm
        """)
        ncm_list = [row[0] for row in connection.execute(query_ncm, {"ano": ano}).fetchall()]

        grafico_ncm_html = ""
        if ncm:
            # Query: evolução anual preço médio do NCM selecionado agrupado pelo filtro
            query_hist = text(f"""
                SELECT 
                    ano,
                    {filtro} AS agrupador,
                    SUM(CASE WHEN ano = :ano_max AND mes <= :mes_max THEN valor ELSE valor END) / 
                    SUM(CASE WHEN ano = :ano_max AND mes <= :mes_max THEN kg ELSE kg END) AS preco_medio
                FROM pescados_dados_{tipo}
                WHERE ncm = :ncm
                GROUP BY ano, {filtro}
                ORDER BY ano
            """)
            df_hist = pd.read_sql_query(query_hist, connection, params={"ncm": ncm, "ano_max": ano_max, "mes_max": mes_max})

            # Gráfico: evolução anual preço médio
            fig = px.line(
                df_hist,
                x="ano",
                y="preco_medio",
                color="agrupador",
                markers=True,
                title=f"Evolução do Preço Médio Anual ({tipo.upper()}) para NCM {ncm}",
                labels={"ano": "Ano", "preco_medio": "Preço Médio (USD/kg)", "agrupador": filtro.capitalize()}
            )
            fig.update_layout(template="plotly_white", height=400)
            grafico_ncm_html = pio.to_html(fig, include_plotlyjs=False, full_html=False)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "pagina": "ncm",
        "ncm_list": ncm_list,
        "grafico_volume": grafico_ncm_html,  # reaproveitamos a posição do gráfico maior
        "grafico_evolucao": "",
        "grafico_categoria": "",
        "grafico_segmento": "",
        "grafico_quantidade": "",
        "tipo": tipo,
        "ano_atual": ano_max,
        "ano_selected": ano,
        "filtro": filtro,
        "filtro_secundario": "",
        "volume": "",
        "valor": "",
        "preco": "",
        "var_volume": "",
        "var_valor": "",
        "var_preco": "",
        "cor_volume": "",
        "cor_valor": "",
        "cor_preco": ""
    })

