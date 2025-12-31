# cleanup_eingabe.py
# Aufruf (Django shell):
#   exec(open("cleanup_eingabe.py", encoding="utf-8").read())
#
# DRY_RUN=True  -> keine DB-Änderungen, nur Ausgabe aller geänderten Datensätze
# DRY_RUN=False -> schreibt Änderungen in die DB
#
# Regeln:
# - "abbr." max 3 (nie aufblasen)
# - "Lsg."  max 3 (nie aufblasen)
# - Marker (1:)/(2:)/(3:): je Marker nur der ERSTE
# - Wertetabellen: gleiche Marker-Regel, nur anderes Längenlimit
# - Single-Eingaben: nur kürzen, keine reinen Whitespace-Änderungen

from core.models import Protokoll
import re

# ---- Settings ----
DRY_RUN = False

MAX_SINGLE = 50
MAX_ANS = 30
MAX_WT = 100        # <<< WICHTIG: Feldgröße
MAX_ABBR = 3
MAX_LSG = 3

MAX_PRINT = 5


DETECT_WERTETABELLE = True
# ------------------

def clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "..."

abbr_re = re.compile(r"(abbr\.\s*,\s*)*abbr\.\s*,?\s*$")

def is_wertetabelle(p: Protokoll) -> bool:
    if not DETECT_WERTETABELLE:
        return False
    try:
        return "tab" in (p.parameter or {}).get("name", "")
    except Exception:
        return False

marker_block_re = re.compile(r"\((\d):\)\s*(.*?)(?=\(\d:\)|\Z)", re.S)

def parse_marker_blocks(s: str):
    return [(m.group(1), m.group(2).strip()) for m in marker_block_re.finditer(s)]

def cut_token_max(s: str, token: str, max_n: int) -> str:
    if s.count(token) <= max_n:
        return s
    kept = 0
    out = []
    i = 0
    while True:
        j = s.find(token, i)
        if j == -1:
            out.append(s[i:])
            break
        out.append(s[i:j])
        if kept < max_n:
            out.append(token)
            kept += 1
        i = j + len(token)
    return "".join(out)

def cleanup_transform(p: Protokoll):
    old = p.eingabe or ""
    if not old:
        return (False, "empty", old, old)

    trimmed = old.strip()
    if not trimmed:
        return (False, "empty", old, old)

    # Lsg. max 3
    if "Lsg." in trimmed:
        t = cut_token_max(trimmed, "Lsg.", MAX_LSG)
        if t != trimmed:
            return (True, "lsg_cut", old, t)
        trimmed = t

    # abbr.-Ketten (nur reine)
    if "abbr." in trimmed and abbr_re.fullmatch(trimmed):
        n = trimmed.count("abbr.")
        if n > MAX_ABBR:
            new = ", ".join(["abbr."] * MAX_ABBR)
            return (True, "abbr_cut", old, new)
        return (False, "abbr_ok", old, old)

    # Marker-Logik
    blocks = parse_marker_blocks(trimmed)
    if blocks:
        out = {}
        for k, txt in blocks:
            if k not in out:
                out[k] = txt

        limit = MAX_WT if is_wertetabelle(p) else MAX_ANS

        new = " ".join(
            f"({k}:) {clip(out[k], limit)}"
            for k in ("1", "2", "3") if k in out
        )

        if new != trimmed:
            return (True, "multi", old, new)

        return (False, "ok", old, old)

    # Single
    if len(trimmed) > MAX_SINGLE:
        new = clip(trimmed, MAX_SINGLE)
        return (True, "single_cut", old, new)

    return (False, "single_ok", old, old)

def main():
    qs = Protokoll.objects.exclude(eingabe__isnull=True)

    total = 0
    would_change = 0
    printed = 0

    for p in qs.iterator(chunk_size=2000):
        total += 1
        did_change, reason, old, new = cleanup_transform(p)

        if did_change:
            would_change += 1  # <-- wichtig: immer zählen, nicht nur beim print

            if printed < 5:
                print(f"\n[{reason}] id={p.id}")
                print("ALT:", old)
                print("NEU:", new)
                print("-" * 60)
                printed += 1

            if not DRY_RUN:
                p.eingabe = new
                p.save(update_fields=["eingabe"])

    print("\nFERTIG")
    print("gesamt:", total)
    print(("wuerde_aendern:" if DRY_RUN else "geaendert:"), would_change)

main()

