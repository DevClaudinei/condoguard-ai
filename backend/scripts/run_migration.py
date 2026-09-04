"""Runner mínimo de migrações SQL contra o DATABASE_URL configurado.

Ponte pragmática até a adoção de Alembic. Executa cada statement do arquivo
.sql dentro de uma única transação (tudo-ou-nada).

Uso (a partir de backend/, com o venv ativo):
    python -m scripts.run_migration migrations/001_created_at_to_timestamptz.sql
"""

import sys
from pathlib import Path

from sqlalchemy import text

from app.database import engine


def _statements(sql: str) -> list[str]:
    # Separa em statements de nível superior. Blocos DO $$ ... $$ são preservados.
    partes: list[str] = []
    buffer: list[str] = []
    em_dollar = False
    for linha in sql.splitlines():
        # Ignora linhas de comentário puro fora de blocos $$ (evita colá-las ao statement).
        if not em_dollar and linha.strip().startswith("--"):
            continue
        if "$$" in linha:
            # Alterna o estado a cada ocorrência de $$ (abre/fecha o corpo).
            em_dollar = em_dollar ^ (linha.count("$$") % 2 == 1)
        buffer.append(linha)
        if not em_dollar and linha.rstrip().endswith(";"):
            partes.append("\n".join(buffer).strip())
            buffer = []
    resto = "\n".join(buffer).strip()
    if resto:
        partes.append(resto)
    return [p for p in partes if p and not p.startswith("--")]


def main(caminho: str) -> None:
    sql = Path(caminho).read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in _statements(sql):
            conn.exec_driver_sql(stmt)
    print(f"Migração aplicada com sucesso: {caminho}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m scripts.run_migration <arquivo.sql>")
    main(sys.argv[1])
