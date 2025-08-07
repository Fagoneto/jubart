import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
database = os.getenv("database")

# Conexão com o banco de dados
engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")

def test_conect():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print("Erro ao conectar:", e)
        return False

def get_dados_anuais_com_mes_corrente(tipo_dado: str, filtro: str, ano: int):
    tabela = f"pescados_dados_{tipo_dado}"
    query = text(f"""
        SELECT ano, mes, {filtro}, SUM(kg) AS volume, SUM(valor) AS valor
        FROM {tabela}
        WHERE ano <= :ano
        GROUP BY ano, mes, {filtro}
        ORDER BY ano, mes
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"ano": ano})
    return df

def get_distribuicao_por_filtro(tipo_dado: str, ano: int, filtro: str):
    tabela = f"pescados_dados_{tipo_dado}"
    query = text(f"""
        SELECT {filtro}, SUM(kg) AS volume
        FROM {tabela}
        WHERE ano = :ano
        GROUP BY {filtro}
        ORDER BY volume DESC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"ano": ano})
    return df

def gerar_grafico_integrado_por_filtro(tipo_dado: str, filtro: str, filtro_2: str):
    nome_tabela = f"pescados_dados_{tipo_dado}"

    with engine.connect() as connection:
        # Ano mais recente
        ano_atual = connection.execute(
            text(f"SELECT MAX(ano) FROM {nome_tabela}")
        ).fetchone()[0]
        if not ano_atual:
            return None, None

        # Histórico
        query_linha = text(f"""
            SELECT ano, {filtro}, SUM(kg) AS volume_total
            FROM {nome_tabela}
            WHERE ano < :ano
            GROUP BY ano, {filtro}
            ORDER BY ano, {filtro}
        """)
        df_linha = pd.read_sql_query(query_linha, con=connection, params={"ano": ano_atual})

        # Sunburst
        query = text(f"""
            SELECT {filtro}, {filtro_2}, SUM(kg) AS volume_total
            FROM {nome_tabela}
            WHERE ano = {ano_atual}
            GROUP BY {filtro}, {filtro_2}
        """)
        df_pizza = pd.read_sql_query(query, con=connection)

    categorias = df_pizza[filtro].unique()
    color_map = {cat: px.colors.qualitative.Plotly[i % 10] for i, cat in enumerate(categorias)}

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.6, 0.4],
        subplot_titles=[
            f"Evolução Anual do Volume por {filtro.title()} (até {ano_atual - 1})",
            f"Distribuição em {ano_atual}"
        ],
        specs=[[{"type": "scatter"}, {"type": "domain"}]]
    )

    for cat in categorias:
        df_cat = df_linha[df_linha[filtro] == cat]
        fig.add_trace(
            go.Scatter(
                x=df_cat["ano"],
                y=df_cat["volume_total"],
                mode="lines+markers",
                name=str(cat),
                marker=dict(color=color_map.get(cat, "#999")),
                line=dict(color=color_map.get(cat, "#999"))
            ),
            row=1, col=1
        )

    fig.add_trace(
        go.Sunburst(
            labels=df_pizza[filtro_2],
            parents=df_pizza[filtro],
            values=df_pizza["volume_total"],
            branchvalues="total",
            marker=dict(colors=[color_map.get(cat, "#999") for cat in df_pizza[filtro]]),
            textinfo='label+percent entry',
            hovertemplate='<b>%{label}</b><br>Volume: %{value:,.0f} kg'
        ),
        row=1, col=2
    )

    fig.update_layout(
        title_text=f"{tipo_dado.upper()} - Volume por {filtro.upper()}",
        height=700,
        template="plotly_white",
        showlegend=True,
        font=dict(size=12)
    )

    return fig, ano_atual

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

