import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def _get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        # Fly/Heroku costumam fornecer postgres:// ; normalize p/ SQLAlchemy 2.x
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        return url
    # Fallback só p/ dev local sem env; em produção queremos Postgres
    return "sqlite:///./local.db"

DATABASE_URL = _get_db_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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


def get_kpis_resumo(engine, tipo: str, ano_final: int) -> dict:
    """
    Retorna KPIs para o 'ano_final' limitando pelo mes_max desse ano.
    Delta é comparado com o mesmo período do ano anterior (mes <= mes_max).
    """
    nome_tabela = f"pescados_dados_{tipo}"

    with engine.connect() as conn:
        # mes_max do ano_final
        mes_max = conn.execute(
            text(f"SELECT MAX(mes) FROM {nome_tabela} WHERE ano=:ano"),
            {"ano": ano_final}
        ).scalar() or 12

        # ano anterior
        ano_ant = ano_final - 1

        # Volume e valor do ano_final até mes_max
        row_atual = conn.execute(text(f"""
            SELECT
              COALESCE(SUM(kg),0)   AS vol,
              COALESCE(SUM(valor),0) AS val
            FROM {nome_tabela}
            WHERE ano=:ano AND mes<=:mes_max
        """), {"ano": ano_final, "mes_max": mes_max}).fetchone()

        vol_atual  = float(row_atual.vol or 0)
        valor_atual = float(row_atual.val or 0)

        # Volume e valor do ano anterior no MESMO recorte de meses
        row_ant = conn.execute(text(f"""
            SELECT
              COALESCE(SUM(kg),0)   AS vol,
              COALESCE(SUM(valor),0) AS val
            FROM {nome_tabela}
            WHERE ano=:ano AND mes<=:mes_max
        """), {"ano": ano_ant, "mes_max": mes_max}).fetchone()

        vol_ant  = float(row_ant.vol or 0)
        valor_ant = float(row_ant.val or 0)

    # preço (médio) = valor/volume, cuidando de divisão por zero
    preco_atual = (valor_atual / vol_atual) if vol_atual else None
    preco_ant   = (valor_ant   / vol_ant)   if vol_ant   else None

    # deltas relativos (ex.: 0.082 = +8.2%)
    def delta_rel(atual, anterior):
        if anterior and anterior != 0:
            return (atual - anterior) / anterior
        return None


    # 🔁 CONVERSÕES DE UNIDADE
    volume_ton_atual   = vol_atual / 1_000.0
    volume_ton_ant     = vol_ant   / 1_000.0
    valor_musd_atual   = valor_atual / 1_000_000.0
    valor_musd_ant     = valor_ant   / 1_000_000.0
    preco_ton_atual    = (preco_atual * 1_000.0) if preco_atual is not None else None
    preco_ton_ant      = (preco_ant   * 1_000.0) if preco_ant   is not None else None

    return {
        # ✅ já nas novas unidades
        "kpi_volume":       volume_ton_atual,   # toneladas
        "kpi_valor":        valor_musd_atual,   # US$ milhões
        "kpi_preco":        preco_ton_atual,    # US$/ton

        # (mantidos para referência se precisar)
        "kpi_volume_ant":   volume_ton_ant,
        "kpi_valor_ant":    valor_musd_ant,
        "kpi_preco_ant":    preco_ton_ant,

        # deltas calculados nas mesmas unidades
        "kpi_volume_delta": delta_rel(volume_ton_atual, volume_ton_ant),
        "kpi_valor_delta":  delta_rel(valor_musd_atual, valor_musd_ant),
        "kpi_preco_delta":  delta_rel(preco_ton_atual,  preco_ton_ant),

        "mes_max":          mes_max,
        "ano_anterior":     ano_ant,
    }


def get_kpis(tipo_dado: str, ano_final: int) -> dict:
    """
    KPIs do topo

    Retorna:
      - volume_atual (kg)
      - volume_atual_ton (toneladas)   <-- novo
      - valor_atual (USD)
      - preco_atual (USD/kg)
      - delta_volume (% vs ano anterior, até o mesmo mes_max)
      - delta_valor  (%)
      - delta_preco  (%)
      - mes_max (int)
    """
    nome_tabela = f"pescados_dados_{tipo_dado}"

    with engine.connect() as conn:
        # último mês disponível no ano selecionado
        mes_max_row = conn.execute(
            text(f"SELECT MAX(mes) FROM {nome_tabela} WHERE ano = :ano"),
            {"ano": ano_final}
        ).fetchone()
        mes_max = mes_max_row[0] if mes_max_row and mes_max_row[0] is not None else 12

        # agrega ano atual e anterior, cortando até mes_max
        q = text(f"""
            SELECT
                SUM(CASE WHEN ano = :ano     AND mes <= :m THEN kg    END) AS vol_atual,
                SUM(CASE WHEN ano = :ano     AND mes <= :m THEN valor END) AS val_atual,
                SUM(CASE WHEN ano = :ano_ant AND mes <= :m THEN kg    END) AS vol_ant,
                SUM(CASE WHEN ano = :ano_ant AND mes <= :m THEN valor END) AS val_ant
            FROM {nome_tabela}
        """)
        r = conn.execute(q, {"ano": ano_final, "ano_ant": ano_final - 1, "m": mes_max}).mappings().one()

    vol_atual = r["vol_atual"] or 0
    val_atual = r["val_atual"] or 0
    vol_ant   = r["vol_ant"]   or 0
    val_ant   = r["val_ant"]   or 0

    preco_atual = (val_atual / vol_atual) if vol_atual else None
    preco_ant   = (val_ant   / vol_ant)   if vol_ant   else None

    def pct(now, prev):
        if not prev:
            return None
        return (now - prev) / prev

    return {
        "volume_atual":      vol_atual,             # kg (compat)
        "volume_atual_ton":  vol_atual / 1000.0,    # toneladas (novo)
        "valor_atual":       val_atual,             # USD
        "preco_atual":       preco_atual,           # USD/kg
        "delta_volume":      pct(vol_atual, vol_ant),
        "delta_valor":       pct(val_atual, val_ant),
        "delta_preco":       pct(preco_atual, preco_ant) if (preco_atual and preco_ant) else None,
        "mes_max":           mes_max,
    }


# def get_distribuicao_volume(engine, tipo_dado: str, ano_final: int, filtro: str) -> pd.DataFrame:
#     """
#     Retorna um DF com distribuição de volume (kg) no ano_final, cortando até o mes_max do ano_final.
#     filtro ∈ {'uf', 'paises', 'ncm', 'especie', 'categoria'}
#     """
#     nome_tabela = f"pescados_dados_{tipo_dado}"

#     # Mapeamento para evitar SQL injection e casar com o nome real da coluna
#     # (ajuste aqui se o nome da coluna na base diferir)
#     COLMAP = {
#         "uf": "uf",
#         "paises": "paises",          # ou 'paises' se sua coluna for assim
#         "ncm": "ncm",
#         "especie": "especie",
#         "categoria": "categoria",
#     }
#     if filtro not in COLMAP:
#         raise ValueError("Filtro inválido.")

#     col = COLMAP[filtro]

#     with engine.connect() as conn:
#         # mes_max do ano escolhido
#         mes_max = conn.execute(
#             text(f"SELECT MAX(mes) FROM {nome_tabela} WHERE ano=:ano"),
#             {"ano": ano_final}
#         ).scalar() or 12

#         # distribuição até mes_max
#         q = text(f"""
#             SELECT {col} AS chave, SUM(kg) AS volume_total
#             FROM {nome_tabela}
#             WHERE ano = :ano AND mes <= :m
#             GROUP BY {col}
#             ORDER BY volume_total DESC
#             LIMIT 20
#         """)
#         df = pd.read_sql_query(q, con=conn, params={"ano": ano_final, "m": mes_max})

#     # Opcional: tratar nulos/rotular "Não informado"
#     if "chave" in df.columns:
#         df["chave"] = df["chave"].fillna("Não informado")

#     return df



def get_distribuicao_volume(engine, tipo_dado: str, ano_final: int, filtro: str) -> pd.DataFrame:
    nome_tabela = f"pescados_dados_{tipo_dado}"

    COLMAP = {
        "paises": "paises",
        "uf": "uf",
        "ncm": "ncm",
        "especie": "especie",
        "categoria": "categoria",
    }
    if filtro not in COLMAP:
        raise ValueError("Filtro inválido.")

    col = COLMAP[filtro]

    with engine.connect() as conn:
        mes_max = conn.execute(
            text(f"SELECT MAX(mes) FROM {nome_tabela} WHERE ano=:ano"),
            {"ano": ano_final}
        ).scalar() or 12

        q = text(f"""
            SELECT {col} AS chave, SUM(kg) AS volume_total
            FROM {nome_tabela}
            WHERE ano = :ano AND mes <= :m
            GROUP BY {col}
            ORDER BY volume_total DESC
            LIMIT 100
        """)
        df = pd.read_sql_query(q, con=conn, params={"ano": ano_final, "m": mes_max})

    if "chave" in df.columns:
        df["chave"] = df["chave"].fillna("Não informado")

    return df



