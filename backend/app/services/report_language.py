"""Cantidades y periodos admitidos por el lenguaje de reportes."""
import calendar
import re
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException

NUMBERS = dict(zip(
    ('cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince '
     'dieciseis diecisiete dieciocho diecinueve veinte veintiuno veintidos veintitres veinticuatro '
     'veinticinco veintiseis veintisiete veintiocho veintinueve').split(), range(30)))
NUMBERS.update({'un': 1, 'una': 1, 'veintiun': 21, 'veintiuna': 21, 'cincuenta': 50, 'cien': 100})
for tens, value in (('treinta', 30), ('cuarenta', 40)):
    NUMBERS[tens] = value
    for units, number in list(NUMBERS.items()):
        if 1 <= number <= 9:
            NUMBERS[f'{tens} y {units}'] = value + number
NUMBER_PATTERN = r'(?:\d+|' + '|'.join(re.escape(n) for n in sorted(NUMBERS, key=len, reverse=True)) + ')'
MONTHS = {name: n for n, name in enumerate(('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'), 1)}


def number_value(value):
    return int(value) if value.isdigit() else NUMBERS[value]


def report_limit(text, filters):
    matches = re.findall(r'\b(' + NUMBER_PATTERN + r')\s+(?:productos?|prendas?|articulos?|categorias?|sucursales?)\b', text)
    matches += re.findall(r'\b(?:top|primeros|primeras|mejores)\s+(' + NUMBER_PATTERN + r')\b', text)
    values = {number_value(value) for value in matches}
    if 'limite' not in filters and len(values) > 1:
        raise HTTPException(422, 'Hay varias cantidades en la solicitud. Indica un solo límite de resultados.')
    try:
        supplied = filters.get('limite', next(iter(values), 10))
        if isinstance(supplied, bool) or isinstance(supplied, float) and not supplied.is_integer():
            raise ValueError
        limit = int(supplied)
    except (TypeError, ValueError):
        raise HTTPException(422, 'El límite debe ser un número entero')
    if not 1 <= limit <= 50:
        raise HTTPException(422, 'El límite debe estar entre 1 y 50')
    return limit


def report_period(text, filters):
    today = datetime.now(timezone(timedelta(hours=-4))).date()
    start, end = today.replace(day=1), today
    iso = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text)
    relative = re.search(r'\bultim[oa]s?\s+(?:(' + NUMBER_PATTERN + r')\s+)?(mes(?:es)?|dias?|semanas?|anos?)\b', text)
    try:
        if iso:
            if len(iso) > 2:
                raise HTTPException(422, 'Indica como máximo una fecha inicial y una final.')
            start, end = date.fromisoformat(iso[0]), date.fromisoformat(iso[-1])
        elif 'ayer' in text or 'hoy' in text:
            if 'ayer' in text and 'hoy' in text:
                if not re.search(r'(?:de|desde|entre) ayer (?:a|hasta|y) hoy', text):
                    raise HTTPException(422, 'Aclara el periodo: puedes pedir desde ayer hasta hoy.')
                start, end = today - timedelta(days=1), today
            else:
                start = end = today - timedelta(days=1 if 'ayer' in text else 0)
        elif 'mes pasado' in text:
            end = today.replace(day=1) - timedelta(days=1)
            start = end.replace(day=1)
        elif relative:
            count = number_value(relative.group(1)) if relative.group(1) else 1
            if count <= 0:
                raise HTTPException(422, 'La cantidad del periodo debe ser positiva.')
            unit = relative.group(2)
            if unit.startswith('mes') or unit.startswith('ano'):
                months = count * (12 if unit.startswith('ano') else 1)
                index = today.year * 12 + today.month - months
                start = date(index // 12, index % 12 + 1, 1)
            else:
                start = today - timedelta(days=count * (7 if unit.startswith('semana') else 1) - 1)
        else:
            if re.search(r'\bultim[oa]s?\b', text) and re.search(r'\b(?:meses?|dias?|semanas?|anos?)\b', text):
                raise HTTPException(422, 'No se pudo interpretar el periodo. Indica, por ejemplo, últimos cinco días o fechas YYYY-MM-DD.')
            month_pattern = r'\b(' + '|'.join(MONTHS) + r')(?:\s+(?:de\s+)?(20\d{2}))?\b'
            named = list(re.finditer(month_pattern, text))
            if len(named) > 2:
                raise HTTPException(422, 'Indica un solo periodo con mes inicial y final.')
            if named:
                year_matches = re.findall(r'\b20\d{2}\b', text)
                default_year = int(year_matches[-1]) if year_matches else today.year
                first, last = named[0], named[-1]
                if len(named) == 2:
                    connector = text[first.end():last.start()].strip()
                    if connector not in {'a', 'hasta', 'y'} or connector == 'y' and not re.search(r'\bentre\s*$', text[:first.start()]):
                        raise HTTPException(422, 'El periodo es ambiguo. Usa de septiembre a octubre de 2026 o fechas YYYY-MM-DD.')
                start = date(int(first.group(2) or default_year), MONTHS[first.group(1)], 1)
                last_year, last_month = int(last.group(2) or default_year), MONTHS[last.group(1)]
                end = date(last_year, last_month, calendar.monthrange(last_year, last_month)[1])
        start = date.fromisoformat(str(filters.get('fecha_desde', start)))
        end = date.fromisoformat(str(filters.get('fecha_hasta', end)))
    except (ValueError, OverflowError):
        raise HTTPException(422, 'Las fechas deben ser válidas y tener formato YYYY-MM-DD')
    if start > end or (end - start).days > 3660:
        raise HTTPException(422, 'El periodo debe estar ordenado y no superar diez años')
    return start, end
