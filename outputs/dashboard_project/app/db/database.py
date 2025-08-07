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


def get_dados_anuais_com_mes_corrente(tipo_dado: str) -> tuple[pd.DataFrame, int, int]:
    """
    Retorna:
    - Um DataFrame com total de volume e valor por ano
    - O ano mais recente
    - O mês mais recente dentro do ano mais recente
    """
    nome_tabela = f"pescados_dados_{tipo_dado}"

    with engine.connect() as connection:
        # Verifica o ano mais recente
        ano_result = connection.execute(
            text(f"SELECT MAX(ano) FROM {nome_tabela}")
        ).fetchone()
        ano_atual = ano_result[0]

        if ano_atual is None:
            return pd.DataFrame(), None, None

        # Verifica o mês mais recente dentro do ano mais recente
        mes_result = connection.execute(
            text(f"SELECT MAX(mes) FROM {nome_tabela} WHERE ano = :ano"),
            {"ano": ano_atual}
        ).fetchone()
        mes_max = mes_result[0]

        if mes_max is None:
            return pd.DataFrame(), None, None

        # Consulta agregada
        query = text(f"""
            SELECT
                ano,
                SUM(kg) AS total_volume,
                SUM(valor) AS total_valor,
                SUM(CASE WHEN mes <= :mes_max THEN kg ELSE 0 END) AS volume_mes_corrente,
                SUM(CASE WHEN mes <= :mes_max THEN valor ELSE 0 END) AS valor_mes_corrente
            FROM {nome_tabela}
            GROUP BY ano
            ORDER BY ano
        """)

        df = pd.read_sql_query(query, con=connection, params={"mes_max": mes_max})

        # ✅ Zera os totais apenas para o ano atual
        df.loc[df['ano'] == ano_atual, ['total_volume', 'total_valor']] = None

        # Formatação do DataFrame
        df_long = pd.melt(
            df,
            id_vars='ano',
            value_vars=['volume_mes_corrente', 'total_volume'],
            var_name='Tipo',
            value_name='Volume'
        )

        df_long['Tipo'] = df_long['Tipo'].map({
            'volume_mes_corrente': 'Volume até Mês Atual (kg)',
            'total_volume': 'Volume Total (kg)'
        })

    return df_long, ano_atual, mes_max

