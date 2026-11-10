# -*- coding: utf-8 -*-
"""Тесты трёх модулей MO2 Translation Tool (stdlib only). Запуск: python test_modules.py"""
from collections import Counter
from text_protect import make_protector, check_placeholders
from glossary import build_matcher
from scanner_status import classify_status

results = []

def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS" if cond else "FAIL"), "-", name)

# --- text_protect ---
protect, restore = make_protector()

t = "Найдено %d из %d предметов"
p = protect(t)
check("P1: два %d защищены", p.count("\u27e6") == 2 and "%d" not in p)
check("P1r: restore возвращает оригинал", restore(p) == t)

t2 = "Здравствуй, {player.name}!\nСтрока вторая"
p2 = protect(t2)
check("P2: брейс-токен и \\n защищены", "{player.name}" not in p2 and "\\n" not in p2)
check("P2r: restore roundtrip", restore(p2) == t2)

t3 = "<font>Y</font> выберите"
p3 = protect(t3)
check("P3: <font>Y</font> — буква Y не доходит до модели",
      "Y" not in p3 and "Д" not in p3)
check("P3r: restore roundtrip", restore(p3) == t3)

t4 = ">Y< and >Z<"
p4 = protect(t4)
check("P4: регресс жадного тега — обе буквы защищены",
      p4.count("\u27e6") == 2)
check("P4r: restore roundtrip", restore(p4) == t4)

t5 = "<b>Жирный</b> и <font color=\"red\">красный</font>"
p5 = protect(t5)
check("P5: теги с атрибутами защищены", "font" not in p5.lower())
check("P5r: restore roundtrip", restore(p5) == t5)

ok, lost = check_placeholders("Найдено %d из %d", "Найдено ⟦0⟧ из ⟦1⟧".replace("⟦0⟧","%d").replace("⟦1⟧","%d"))
check("P6: мультимножество — два %d в src и dst", ok and not lost)
ok2, lost2 = check_placeholders("Найдено %d из %d", "Найдено %d штук")
check("P7: потерянный токен обнаружен", not ok2 and lost2 == ["%d"])

check("P8: пустые строки безопасны", protect("") == "" and restore("") == "")

# --- glossary ---
g = {"Dark Brotherhood": "Тёмное Братство", "Wolf": "Волк", "men": "люди"}
apply_g = build_matcher(g)
s = "The Dark Brotherhood and a wolf and men MENUS"
r = apply_g(s)
check("G1: длинный термин раньше короткого", "Тёмное Братство" in r)
check("G2: регистр не важен", "Волк" in r)
check("G3: граница слов — MENUS не задет", "MENUS" in r and "люди" in r)
check("G4: однопроходность — вставленный текст не сканируется",
      apply_g("Wolf") == "Волк")
check("G5: пустой глоссарий — текст без изменений", build_matcher({})("abc") == "abc")

# --- scanner_status ---
en = [f"Item name {i}" for i in range(200)]
ru = list(en); ru[50] = "Иван"
check("S1: 'Иван' среди 200 строк — not_translated",
      classify_status(en, ru) == "not_translated")
ru_full = [f"Предмет {i}" for i in range(200)]
check("S2: полный перевод — translated", classify_status(en, ru_full) == "translated")
ru_half = [f"Предмет {i}" if i < 120 else en[i] for i in range(200)]
check("S3: больше половины — translated (0.6>=0.6)", classify_status(en, ru_half) == "translated")
ru_q = [f"Предмет {i}" if i < 60 else en[i] for i in range(200)]
check("S4: 30% — partial", classify_status(en, ru_q) == "partial")
check("S5: пустой вход — empty", classify_status([], []) == "empty")
check("S6: ничего не изменено — not_translated",
      classify_status(["a", "b"], ["a", "b"]) == "not_translated")

failed = [n for n, ok in results if not ok]
print(f"\nИтого: {len(results) - len(failed)}/{len(results)} PASS")
if failed:
    print("FAILURES:", failed)
    raise SystemExit(1)
