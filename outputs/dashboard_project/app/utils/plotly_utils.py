import plotly.express as px
import plotly.io as pio

def gerar_grafico_plotly(dados):
    fig = px.bar(x=[d[0] for d in dados], y=[d[1] for d in dados],
                 labels={"x": "País", "y": "Volume"}, title="Volume de Exportação")
    return pio.to_html(fig, include_plotlyjs="cdn", full_html=False)
