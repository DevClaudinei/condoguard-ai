-- Migração 001: converte chamados.created_at para timestamptz.
--
-- Bancos criados antes da mudança para DateTime(timezone=True) têm a coluna como
-- "timestamp without time zone". Os valores foram gravados em UTC (datetime.utcnow),
-- portanto reinterpretamos o horário existente como UTC ao converter.
--
-- Idempotência: o bloco só altera a coluna se ela ainda NÃO for timestamptz.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'chamados'
          AND column_name = 'created_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE chamados
            ALTER COLUMN created_at TYPE timestamptz
            USING created_at AT TIME ZONE 'UTC';
    END IF;
END $$;

ALTER TABLE chamados
    ALTER COLUMN created_at SET DEFAULT now();
