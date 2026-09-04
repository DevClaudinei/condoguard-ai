#!/usr/bin/env bash
#
# Varredura anti-segredos (sem dependências externas). Detecta:
#   - Access keys AWS (AKIA/ASIA)
#   - Chaves privadas (RSA/EC/OPENSSH/PGP/DSA)
#   - Tokens do GitHub (ghp_, github_pat_)
#   - Segredos AWS em config (aws_secret_access_key / aws_session_token = ...)
#   - ARNs com ID de conta REAL (12 dígitos) — o placeholder 123456789012 é permitido
#
# Uso:
#   scripts/secret-scan.sh                 # varre todos os arquivos versionados
#   scripts/secret-scan.sh <arq1> <arq2>   # varre apenas os informados (ex.: pre-commit)
#
set -uo pipefail

ALLOW_ACCOUNT="123456789012"   # placeholder canônico da AWS (permitido em docs/exemplos)
SELF="scripts/secret-scan.sh"  # não varrer o próprio scanner (contém os regex)

if [[ $# -gt 0 ]]; then
  mapfile -t CANDIDATOS < <(printf '%s\n' "$@")
else
  mapfile -t CANDIDATOS < <(git ls-files)
fi

FILES=()
for f in "${CANDIDATOS[@]}"; do
  [[ -f "$f" ]] || continue
  [[ "$f" == "$SELF" ]] && continue
  case "$f" in
    *node_modules/*|*.venv/*|*/.venv/*|*cdk.out/*|*.git/*) continue ;;
    *.png|*.jpg|*.jpeg|*.gif|*.ico|*.pdf|*.woff|*.woff2|*.ttf) continue ;;
    *package-lock.json|*.lock) continue ;;
  esac
  FILES+=("$f")
done

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "Nenhum arquivo a varrer."
  exit 0
fi

# ERE combinada. -I ignora binários; -n numera linhas.
PATTERNS='AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[0-9A-Za-z]{36}|github_pat_[0-9A-Za-z_]{22,}|(aws_secret_access_key|aws_session_token)[[:space:]]*[=:]|arn:aws:[a-z0-9-]*:[a-z0-9-]*:[0-9]{12}:'

HITS=$(grep -EnI "$PATTERNS" "${FILES[@]}" 2>/dev/null \
  | grep -vE "arn:aws:[a-z0-9-]*:[a-z0-9-]*:${ALLOW_ACCOUNT}:" || true)

if [[ -n "$HITS" ]]; then
  echo "🚨 Possíveis segredos / dados sensíveis detectados:" >&2
  echo "$HITS" >&2
  echo >&2
  echo "Remova o dado do commit. Se for falso positivo legítimo (ex.: placeholder)," >&2
  echo "ajuste a allowlist em ${SELF}." >&2
  exit 1
fi

echo "✅ Varredura anti-segredos: nada encontrado (${#FILES[@]} arquivos)."
exit 0
