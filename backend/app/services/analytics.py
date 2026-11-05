"""Regresión lineal y K-means reproducibles, con evaluación fuera del entrenamiento."""

import math
import random
from statistics import mean, pstdev

FEATURES = ["precio", "stock", "descuento", "mes_seno", "mes_coseno", "fin_de_semana"]


def features(price, stock, discount, month, weekday):
    return [price, stock, discount, math.sin(month * math.tau / 12), math.cos(month * math.tau / 12), int(weekday >= 5)]


def _distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _solve(matrix, values):
    rows = [list(row) + [value] for row, value in zip(matrix, values)]
    for i in range(len(rows)):
        pivot = max(range(i, len(rows)), key=lambda j: abs(rows[j][i]))
        rows[i], rows[pivot] = rows[pivot], rows[i]
        divisor = rows[i][i]
        if abs(divisor) < 1e-12:
            raise ValueError("Datos insuficientes para ajustar la regresión")
        rows[i] = [value / divisor for value in rows[i]]
        for j in range(len(rows)):
            if j != i:
                factor = rows[j][i]
                rows[j] = [x - factor * y for x, y in zip(rows[j], rows[i])]
    return [row[-1] for row in rows]


def standardize(values, centers, scales):
    return [(x - center) / scale for x, center, scale in zip(values, centers, scales)]


def predict(model, values):
    vector = standardize(values, model["medias"], model["escalas"])
    prediction = model["coeficientes"][0] + sum(x * weight for x, weight in zip(vector, model["coeficientes"][1:]))
    distances = [_distance(vector, center) for center in model["centroides"]]
    cluster = distances.index(min(distances))
    return max(0.0, prediction), cluster, min(distances)


def train(seed=42, samples=480):
    rng = random.Random(seed)
    dataset = []
    for _ in range(samples):
        vector = features(rng.uniform(30, 450), rng.randint(0, 150), rng.choice([0, 0.1, 0.2, 0.3]), rng.randint(1, 12), rng.randint(0, 6))
        price, stock, discount, sine, cosine, weekend = vector
        demand = max(0, 25 - price * 0.035 + stock * 0.025 + discount * 35 + sine * 4 + cosine * 2 + weekend * 3 + rng.gauss(0, 1.8))
        dataset.append((vector, demand))
    rng.shuffle(dataset)
    training, test = dataset[:int(samples * 0.8)], dataset[int(samples * 0.8):]
    centers = [mean(row[0][i] for row in training) for i in range(len(FEATURES))]
    scales = [pstdev(row[0][i] for row in training) or 1 for i in range(len(FEATURES))]
    x = [[1, *standardize(row, centers, scales)] for row, _ in training]
    y = [target for _, target in training]
    count = len(FEATURES) + 1
    matrix = [[sum(row[i] * row[j] for row in x) + (1e-6 if i == j else 0) for j in range(count)] for i in range(count)]
    rhs = [sum(row[i] * target for row, target in zip(x, y)) for i in range(count)]
    weights = _solve(matrix, rhs)
    normalized = [row[1:] for row in x]
    centroids = [normalized[0]]
    while len(centroids) < 3:
        centroids.append(max(normalized, key=lambda row: min(_distance(row, center) for center in centroids)))
    iterations = 0
    for iterations in range(1, 101):
        groups = [[] for _ in centroids]
        for row in normalized:
            label = min(range(3), key=lambda i: _distance(row, centroids[i]))
            groups[label].append(row)
        updated = [[mean(row[i] for row in group) for i in range(len(FEATURES))] if group else center for group, center in zip(groups, centroids)]
        if max(_distance(a, b) for a, b in zip(updated, centroids)) < 1e-6:
            centroids = updated
            break
        centroids = updated
    model = {"medias": centers, "escalas": scales, "coeficientes": weights, "centroides": centroids}
    predictions = [predict(model, row)[0] for row, _ in test]
    actual = [target for _, target in test]
    errors = [prediction - target for prediction, target in zip(predictions, actual)]
    denominator = sum((target - mean(actual)) ** 2 for target in actual)
    test_points = [standardize(row, centers, scales) for row, _ in test]
    labels = [min(range(3), key=lambda i: _distance(row, centroids[i])) for row in test_points]
    silhouettes = []
    for i, row in enumerate(test_points):
        own = [_distance(row, other) for j, other in enumerate(test_points) if i != j and labels[j] == labels[i]]
        others = [[_distance(row, other) for j, other in enumerate(test_points) if labels[j] == label] for label in range(3) if label != labels[i]]
        if not own or not any(others):
            silhouettes.append(0.0)
        else:
            a, b = mean(own), min(mean(group) for group in others if group)
            silhouettes.append((b - a) / max(a, b) if max(a, b) else 0.0)
    distances = [predict(model, row)[2] for row, _ in training]
    model["umbral_anomalia"] = mean(distances) + 2 * pstdev(distances)
    model["evaluacion"] = {"mae": round(mean(abs(e) for e in errors), 4),
        "rmse": round(math.sqrt(mean(e * e for e in errors)), 4),
        "r2": round(1 - sum(e * e for e in errors) / denominator, 4),
        "silhouette": round(mean(silhouettes), 4), "muestras_entrenamiento": len(training),
        "muestras_validacion": len(test), "iteraciones_kmeans": iterations}
    model["variables"] = FEATURES
    model["fuente_entrenamiento"] = "SINTETICA"
    model["semilla"] = seed
    return model
