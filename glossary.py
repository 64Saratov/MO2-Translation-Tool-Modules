# -*- coding: utf-8 -*-
"""
glossary — постобработка перевода глоссарием.
MO2 Translation Tool, candidate module for upstream 3.5.0 integration.

Применяется ПОСЛЕ получения ответа модели (и после кэша): термин из
глоссария, присутствующий в оригинале, но оставшийся в переводе
нетронутым (в любой раскладке и регистре), заменяется глоссарным переводом.

Свойства:
- длинные термины сопоставляются раньше коротких ("Dark Brotherhood"
  не расползается в "Тёмное Братство Братство");
- замены по границам слов, без учёта регистра;
- однопроходность: вставленный перевод не сканируется повторно,
  рекурсивных мутаций нет ("Wolf" -> "Волк" не превращается в
  "Волк"-ключ второго прохода).

Только стандартная библиотека. Зависимостей от Qt/mobase нет.
"""

import re

_WORD_BOUNDRY_LEFT = r"(?<![A-Za-z\u00C0-\u024F\u0400-\u04FF])"
_WORD_BOUNDRY_RIGHT = r"(?![A-Za-z\u00C0-\u024F\u0400-\u04FF])"


def build_matcher(glossary: dict):
    """Строит функцию apply(text) -> str по словарю {термин: перевод}."""
    items = []
    for term, trans in (glossary or {}).items():
        t = (term or "").strip()
        tr = (trans or "").strip()
        if t and tr and t.lower() != tr.lower():
            items.append((t, tr))
    if not items:
        return lambda text: text or ""

    # длинные термины раньше коротких
    items.sort(key=lambda p: len(p[0]), reverse=True)
    pattern = re.compile(
        _WORD_BOUNDRY_LEFT + "(" + "|".join(re.escape(t) for t, _ in items) + ")" + _WORD_BOUNDRY_RIGHT,
        re.IGNORECASE,
    )
    mapping = {}
    for t, tr in items:
        mapping.setdefault(t.lower(), tr)

    def apply(text: str) -> str:
        if not text:
            return text or ""
        return pattern.sub(lambda m: mapping[m.group(0).lower()], text)

    return apply
