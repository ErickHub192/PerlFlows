import re

# Patrón simple para cada campo cron: números, asterisco, guión, coma y barra
CRON_FIELD_PATTERN = re.compile(r"^(?:\*|\d+)(?:-\d+)?(?:/\d+)?(?:,(?:\*|\d+)(?:-\d+)?(?:/\d+)?)*$")


def validate_cron_expression(expr: str) -> bool:
    """
    Valida que `expr` sea una expresión cron de 5 campos:
      - cada campo puede ser '*', número, rango (e.g. '1-5'), paso (e.g. '*/15'), o lista separada por comas.
    Devuelve True si cumple el patrón, False en caso contrario.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    return all(CRON_FIELD_PATTERN.match(p) for p in parts)
