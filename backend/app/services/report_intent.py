"""Clasificador Naive Bayes local para las intenciones de los reportes."""
import math
import re
import unicodedata
from collections import Counter

EXAMPLES = {
    "ventas": ["ventas por sucursal", "cuanto vendimos este mes", "facturacion de las tiendas", "resumen de ingresos", "comparar ventas mensuales", "grafico de ventas semanales"],
    "productos": ["productos mas vendidos", "top de prendas compradas", "ranking de productos", "que ropa se vende mas", "las diez prendas con mayores ingresos"],
    "categorias": ["ingresos por categoria", "categorias con mayores ventas", "facturacion por categoria", "que categorias aportan mas dinero"],
    "inventario": ["productos con stock bajo", "inventario de las sucursales", "prendas con menores existencias", "que ropa necesita reposicion", "faltantes de mercaderia", "existencias disponibles"],
    "reservas": ["reservas por estado", "cuantas prendas estan reservadas", "resumen de apartados de ropa", "reservas pendientes de atencion", "estado de las reservas"],
}


def _tokens(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')
    return [word for word in re.findall(r'[a-z]+', text) if len(word) > 2]


COUNTS = {label: Counter(word for text in examples for word in _tokens(text)) for label, examples in EXAMPLES.items()}
VOCABULARY = set().union(*(counts.keys() for counts in COUNTS.values()))


def classify(question):
    tokens = [word for word in _tokens(question) if word in VOCABULARY]
    if not tokens:
        return None, 0.0
    scores = {}
    for label, counts in COUNTS.items():
        total = sum(counts.values()) + len(VOCABULARY)
        scores[label] = math.log(1 / len(COUNTS)) + sum(math.log((counts[word] + 1) / total) for word in tokens)
    best = max(scores, key=scores.get)
    scale = max(scores.values())
    probabilities = {label: math.exp(score-scale) for label, score in scores.items()}
    confidence = probabilities[best] / sum(probabilities.values())
    return best, confidence
