import plotly.express as px
import plotly.io as pio
import pandas as pd
import plotly.graph_objects as go

def grafico_historico_volume_preco(df: pd.DataFrame, tipo_dado: str) -> str:
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["ano"],
        y=df["volume_mes_corrente"] / 1_000_000,
        name="Volume (x1000 ton)",
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
        yaxis=dict(title="Volume (x1000 ton)", showgrid=False),
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
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        bargap=0.2,
        autosize=True,
        height=420,
        margin=dict(l=20, r=20, t=40, b=40)
    )

    # 🔥 ESSENCIAL: gerar HTML responsivo
    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False},
        default_width="100%",      # Já força 100%
        default_height="420px"     # Ou outro valor fixo se preferir
    )

def grafico_evolucao_mensal(df_mensal: pd.DataFrame) -> str:
    df = df_mensal.copy()
    df.rename(columns={'ano': 'year', 'mes': 'month', 'total_volume': 'volume'}, inplace=True)
    df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
    df['cumulative_volume'] = df.groupby('year')['volume'].cumsum()
    df['cumulative_volume'] = df['cumulative_volume']/1000000

    current_year = df['year'].max()
    last_year = current_year - 1
    historical_df = df[df['year'] < current_year]

    fig = px.box(
        historical_df,
        x='month',
        y='cumulative_volume',
        labels={'cumulative_volume': 'Volume Acumulado (kg)', 'month': 'Mês'},
        color_discrete_sequence=['lightblue']
    )

    # Linha do ano anterior
    df_last_year = df[df['year'] == last_year]
    fig.add_trace(go.Scatter(
        x=df_last_year['month'],
        y=df_last_year['cumulative_volume'],
        mode='lines+markers',
        name=f'{last_year} Acumulado',
        line=dict(color='blue', width=2)
    ))

    # Linha do ano atual
    df_current_year = df[df['year'] == current_year]
    fig.add_trace(go.Scatter(
        x=df_current_year['month'],
        y=df_current_year['cumulative_volume'],
        mode='lines+markers',
        name=f'{current_year} Acumulado',
        line=dict(color='red', width=3)
    ))

    fig.update_layout(
        title='Evolução Mensal Acumulada de Volume',
        xaxis_title='Mês',
        yaxis_title='Volume Acumulado (x1000 ton)',
        plot_bgcolor='white',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        autosize=True,
        margin=dict(l=20, r=20, t=40, b=40)
    )

    # 🔥 ESSENCIAL: gerar HTML responsivo
    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False},
        default_width="100%",      # Já força 100%
        default_height="420px"     # Ou outro valor fixo se preferir
    )




def grafico_distribuicao_volume(
    df: pd.DataFrame,
    label: str = "País",
    top_n: int = 20
) -> str:
    """Gera um donut da distribuição de volume por 'chave' (já agregada no DF)."""
    if df is None or df.empty:
        return "<div style='padding:12px'>Sem dados para este filtro.</div>"

    # garante apenas top_n
    df = df.nlargest(top_n, "volume_total")

    fig = px.pie(
        df,
        names="chave",           # <- vindo do get_distribuicao_volume
        values="volume_total",
        hole=0.35,
        title=f"Distribuição do Volume por {label}"
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=380)

    return pio.to_html(fig, include_plotlyjs="cdn", full_html=False)



