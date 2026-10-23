def normalize(value: str) -> str:
    """Valor para comparação (`*_norm`): `strip()` + `casefold()` (04-data-model.md)."""
    return value.strip().casefold()
