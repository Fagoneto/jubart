from fastapi import APIRouter
from sqlalchemy import text
from app.db.database import engine

router = APIRouter()

@router.get("/debug/db")
def debug_db(tipo: str = "impo"):
    tabela = f"pescados_dados_{tipo}"

    with engine.connect() as c:
        try:
            dbname = c.execute(text("SELECT current_database()")).scalar()
        except Exception:
            dbname = "N/A"

        count = c.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
        ano_max = c.execute(text(f"SELECT MAX(ano) FROM {tabela}")).scalar()
        mes_max = c.execute(
            text(f"SELECT MAX(mes) FROM {tabela} WHERE ano=:a"),
            {"a": ano_max}
        ).scalar()

    return {
        "engine_url": str(engine.url),
        "database": dbname,
        "tabela": tabela,
        "rows": int(count or 0),
        "ano_max": ano_max,
        "mes_max": mes_max,
    }
