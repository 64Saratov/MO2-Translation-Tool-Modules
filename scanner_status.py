# -*- coding: utf-8 -*-
"""
scanner_status — coverage-детекция статуса перевода мода.
MO2 Translation Tool, candidate module for upstream 3.5.0 integration.

Замена эвристики "в строках есть кириллица -> мод переведён".
Статус считается по ДОЛЕ ключей, у которых RU-значение отличается
от EN-оригинала. Имя NPC "Иван" среди двухсот английских строк даёт
долю 0.5% — статус "not_translated", а не ложное "translated".

Статусы: "translated" | "partial" | "not_translated" | "empty"

Только стандартная библиотека. Зависимостей от Qt/mobase нет.
"""

DEFAULT_THRESHOLD = 0.6   # доля изменённых строк для статуса "translated"
DEFAULT_MIN_SAMPLE = 8    # при меньшем числе строк порог смягчается
PARTIAL_FLOOR = 0.15      # минимальная доля для "partial"

def classify_status(en_values, ru_values,
                    threshold: float = DEFAULT_THRESHOLD,
                    min_sample: int = DEFAULT_MIN_SAMPLE) -> str:
    """en_values/ru_values — последовательности значений строк по ОБЩИМ ключам
    (порядок и длина должны совпадать; caller отвечает за выравнивание)."""
    en = list(en_values or [])
    if not en:
        return "empty"
    ru = list(ru_values or [])
    # выравнивание по длине на случай расхождений
    n = min(len(en), len(ru)) if ru else 0
    changed = sum(
        1 for i in range(n)
        if (ru[i] or "").strip() and (ru[i] or "").strip() != (en[i] or "").strip()
    )
    total = len(en)
    ratio = changed / total
    if ratio >= threshold:
        return "translated"
    # при малых выборках порог смягчается: 3 изменённые строки из 5 — уже partial
    if changed >= 3 or (changed > 0 and ratio >= PARTIAL_FLOOR):
        return "partial"
    return "not_translated"
