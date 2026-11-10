# -*- coding: utf-8 -*-
"""
text_protect — защита нетранслируемых фрагментов текста перед отправкой в LLM.
MO2 Translation Tool, candidate module for upstream 3.5.0 integration.

Защищает: форматные токены (%d, %s, %1$s, %%), брейс-токены ({0}, {player.name}),
литеральный \n, HTML/BBCode-подобные теги (<b>, </font>, <br/>, <font color="red">)
и одиночные латинские буквы, зажатые между скобками (>Y<).

Порядок проходов важен: одиночные буквы защищаются ПЕРВЫМИ, до тегов —
иначе в цепочке ">Y< and >Z<" жадное сопоставление тегов способно
склеить фрагменты в фиктивный тег и потерять защиту.

Только стандартная библиотека. Зависимостей от Qt/mobase нет.
"""

import re
from collections import Counter

PLACEHOLDER_OPEN = "\u27e6"   # ⟦
PLACEHOLDER_CLOSE = "\u27e7"  # ⟧

# Форматные токены, брейсы, литеральный \n и теги.
_TOKEN_RE = re.compile(
    r"%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[hlL]?[diouxXeEfgGaAcspn%]"   # %d, %s, %1$s, %%
    r"|\{[^{}\n]{0,64}\}"                                           # {0}, {player.name}
    r"|\\n"                                                          # литеральный \n
    r"|</?[A-Za-z][^\s<>]{0,63}(?:\s[^<>]{0,120})?/?>"               # <b>, </font>, <br/>
)

# Одиночная латинская буква между скобками: <font>Y</font>, >Y< and >Z<
_LONE_LETTER_RE = re.compile(r"(?<=>)[A-Za-z](?=<)")

_PH_RE_CACHE = {}

def make_protector(prefix: str = PLACEHOLDER_OPEN, suffix: str = PLACEHOLDER_CLOSE):
    """Возвращает пару функций (protect, restore) с общим хранилищем.

    Одна пара — на один запрос к модели (или на поток). protect() заменяет
    защищаемые фрагменты плейсхолдерами ⟦N⟧, restore() возвращает их на место.
    Повторный protect() защищённого текста безопасен (idempotent guard):
    уже стоящие плейсхолдеры перезащищаются как есть.
    """
    store = {}

    def protect(text: str) -> str:
        if not text:
            store.clear()
            return text or ""
        store.clear()
        idx = [0]

        def _put(m: "re.Match") -> str:
            ph = f"{prefix}{idx[0]}{suffix}"
            idx[0] += 1
            store[ph] = m.group(0)
            return ph

        # 1) одиночные буквы между скобками — ДО тегов
        s = _LONE_LETTER_RE.sub(_put, text)
        # 2) теги, плейсхолдеры формата, брейсы, \n
        s = _TOKEN_RE.sub(_put, s)
        return s

    def restore(text: str) -> str:
        if not text or not store:
            return text or ""
        ph_re = _PH_RE_CACHE.get((prefix, suffix))
        if ph_re is None:
            ph_re = re.compile(re.escape(prefix) + r"\d+" + re.escape(suffix))
            _PH_RE_CACHE[(prefix, suffix)] = ph_re
        return ph_re.sub(lambda m: store.get(m.group(0), m.group(0)), text)

    return protect, restore


def check_placeholders(src: str, dst: str) -> "tuple[bool, list]":
    """Пост-проверка перевода: все токены из src обязаны присутствовать в dst.
    Сравнение мультимножествами: два %d в исходнике требуют двух %d в переводе.
    Возвращает (ok, lost): ok=False, если хотя бы один токен потерян."""
    src_tokens = _TOKEN_RE.findall(src or "")
    if not src_tokens:
        return True, []
    dst_counts = Counter(_TOKEN_RE.findall(dst or ""))
    lost = []
    for t in src_tokens:
        if dst_counts.get(t, 0) > 0:
            dst_counts[t] -= 1
        elif t not in lost:
            lost.append(t)
    return (not lost), lost


def has_missing_placeholders(src: str, dst: str) -> bool:
    return not check_placeholders(src, dst)[0]
