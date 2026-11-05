from decimal import Decimal, ROUND_HALF_UP


def money(value) -> Decimal:
    """Importes en centavos, con la misma regla para catálogo y cobro."""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
