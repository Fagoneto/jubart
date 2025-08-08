import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


load_dotenv()

# Constrói o engine
user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
database = os.getenv("database")

# Verificação opcional (pode remover depois de testar)
if not all([user, password, host, port, database]):
    print("🚀 USER:", user)
    print("🚀 PASSWORD:", password)
    print("🚀 HOST:", host)
    print("🚀 PORT:", port)
    print("🚀 DATABASE:", database)

    raise ValueError("❌ Variáveis de ambiente não foram carregadas corretamente.")

# Cria engine de conexão com o PostgreSQL
engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")



def get_ano_mes_max(nome_tabela: str) -> tuple[int, int] | tuple[None, None]:
    """
    Retorna:
    - o ano mais recente (`ano_atual`)
    - o mês mais recente (`mes_max`) dentro do ano mais recente

    Caso não existam dados, retorna (None, None)
    """
    with engine.connect() as connection:
        # Ano mais recente
        ano_result = connection.execute(
            text(f"SELECT MAX(ano) FROM {nome_tabela}")
        ).fetchone()
        ano_atual = ano_result[0]

        if ano_atual is None:
            return None, None

        # Mês mais recente dentro do ano mais recente
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM {nome_tabela} WHERE ano = :ano"),
            {"ano": ano_atual}
        ).fetchone()
        mes_max = mes_result[0]

        if mes_max is None:
            return None, None

    return ano_atual, mes_max


def get_dados_volume_preco(engine, tipo_dado: str, ano_final: int) -> pd.DataFrame:
    ano_min = ano_final - 5

    with engine.connect() as connection:
        # Buscar mês máximo para o ano selecionado
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM pescados_dados_{tipo_dado} WHERE ano = :ano"),
            {"ano": ano_final}
        ).fetchone()
        mes_max = mes_result[0] if mes_result and mes_result[0] is not None else 12

        # Buscar dados agregados
        query = text(f"""
            SELECT
                ano,
                SUM(CASE WHEN mes <= :mes_max THEN kg ELSE 0 END) AS volume_mes_corrente,
                SUM(CASE WHEN mes <= :mes_max THEN valor ELSE 0 END) AS valor_mes_corrente
            FROM pescados_dados_{tipo_dado}
            WHERE ano BETWEEN :ano_min AND :ano_max
            GROUP BY ano
            ORDER BY ano
        """)

        df = pd.read_sql_query(query, con=connection, params={
            "mes_max": mes_max,
            "ano_min": ano_min,
            "ano_max": ano_final
        })

        # Calcular preço médio
        df["preco_medio"] = df["valor_mes_corrente"] / df["volume_mes_corrente"]
        return df


def get_dados_evolucao_mensal(engine, tipo_dado: str, ano_final: int) -> pd.DataFrame:
    ano_min = ano_final - 5
    with engine.connect() as connection:
        # Verifica o mês máximo do ano final
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM pescados_dados_{tipo_dado} WHERE ano = :ano_final"),
            {"ano_final": ano_final}
        ).fetchone()
        mes_max = mes_result[0] if mes_result and mes_result[0] is not None else 12

        # Consulta de volumes por mês
        query = text(f"""
            SELECT
                ano,
                mes,
                SUM(kg) AS total_volume
            FROM pescados_dados_{tipo_dado}
            WHERE ano BETWEEN :ano_min AND :ano_final
            GROUP BY ano, mes
            ORDER BY ano, mes
        """)
        df = pd.read_sql_query(query, con=connection, params={"ano_min": ano_min, "ano_final": ano_final})

    return df






