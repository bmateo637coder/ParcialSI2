"""CU19 — Procesar pago electrónico.

Abstracción de una pasarela de pagos. En producción simula Stripe en modo
sandbox: las tarjetas de prueba devuelven éxito y dos números conocidos
generan rechazos para poder probar el flujo de fallo en cualquier entorno.
"""

import secrets
from dataclasses import dataclass

# Tarjetas de prueba que la pasarela sandbox rechaza siempre.
DECLINED_TEST_CARDS = {"4000000000000002", "4000000000009995"}


@dataclass
class GatewayResult:
    success: bool
    transaction_id: str | None
    error: str | None = None


class PaymentGateway:
    """Interfaz de la pasarela de pagos."""

    def charge(self, amount: float, method: str, metadata: dict | None = None) -> GatewayResult:
        raise NotImplementedError


class SandboxPaymentGateway(PaymentGateway):
    """Simula la pasarela de Stripe (modo sandbox)."""

    def charge(self, amount: float, method: str, metadata: dict | None = None) -> GatewayResult:
        meta = metadata or {}
        card = (meta.get("card_number") or "").replace(" ", "").replace("-", "")

        if amount <= 0:
            return GatewayResult(False, None, "El monto del pago debe ser mayor a cero")

        if method == "TARJETA" and card in DECLINED_TEST_CARDS:
            return GatewayResult(
                False,
                f"pi_sandbox_declined_{secrets.token_hex(8)}",
                "La tarjeta fue rechazada por la pasarela (modo sandbox)",
            )

        transaction_id = f"pi_sandbox_{secrets.token_hex(8)}"
        return GatewayResult(True, transaction_id, None)


def get_gateway() -> PaymentGateway:
    return SandboxPaymentGateway()