"""Remove embedded tutorial code and UI noise from extracted article bodies."""

from __future__ import annotations

import re

# WordPress / tutorial widgets (MarkTechPost-style)
_COPY_CODE_CHUNK = re.compile(
    r"(?i)\s*Copy Code\s+Copied\s+Use a different Browser\s*"
)
_COPY_CODE_SHORT = re.compile(r"(?i)\s*Copy Code\s+Copied\s*")
_FULL_CODES = re.compile(r"(?i)\s*Check out the Full Codes\.?\s*")

# Cuts marketing / syndication tail (same line or after newline)
_ALSO_FOLLOW_TAIL = re.compile(r"(?is)\.\s+Also, feel free to follow\b.*$")
_THE_POST_TAIL = re.compile(
    r"(?is)(?:\n|^)\s*The post .+ appeared first on .+$"
)
# Inline "The post … appeared first on …" without a preceding newline
_THE_POST_INLINE = re.compile(r"(?is)\s+The post .+ appeared first on .+$")

# Lines that strongly resemble Python / shell / config (tutorial dumps)
_IMPORT = re.compile(r"^(?:import |from [\w.]+\s+import\s+)")
_DEF_CLASS = re.compile(r"^(?:def |async def |class )[\w]")
_DECORATOR = re.compile(r"^@[\w.]+(?:\([^)]*\))?\s*$")
_CONTROL = re.compile(
    r"^(?:if |elif |else:|for |while |with |try:|except\b|finally:|raise |return |yield )"
)
_SHELLISH = re.compile(r"^(?:\$\s|>\s|pip install|apt-get|git clone|cd /|rm -rf )", re.I)


def _line_looks_like_code(ln: str) -> bool:
    s = ln.strip()
    if len(s) < 2:
        return False
    if _IMPORT.search(s):
        return True
    if _DEF_CLASS.search(s):
        return True
    if _DECORATOR.match(s):
        return True
    if _CONTROL.search(s):
        return True
    if _SHELLISH.search(s):
        return True
    if s.startswith("print(") or s.startswith("logger."):
        return True
    # Tutorial-style constants: BASE_MODEL_PATH = "..."
    if re.match(r"^[A-Z][A-Z0-9_]{2,}\s*=\s*", s):
        return True
    # One-line call with many nested parens / brackets (typical ML APIs)
    if (
        re.match(r"^[A-Za-z_][\w.]*\(", s)
        and len(s) > 50
        and s.count("(") >= 2
        and s.count("=") <= max(2, len(s) // 80)
    ):
        return True
    # Keyword=value API style lines
    if re.match(
        r"^[A-Za-z_][\w.]*\s*=\s*[^=]{8,}",
        s,
    ) and (s.count("=") >= 2 or "torch." in s or "np." in s or "self." in s):
        return True
    return False


def _scrub_inline_statement_tails(text: str) -> str:
    """Drop ``. import …`` / ``. from … import …`` tails (collapsed HTML)."""
    tail = re.compile(
        r"(?i)(.*[.!?]\s)(?:\bimport\s+[\w,. ]+|\bfrom\s+[\w.]+\s+import\s+[\w,. ]+)\s*$"
    )
    only_stmt = re.compile(
        r"(?i)^(?:\bimport\s+[\w,. ]+|\bfrom\s+[\w.]+\s+import\s+[\w,. ]+)$"
    )
    out_lines: list[str] = []
    for line in text.splitlines():
        m = tail.match(line)
        if m:
            out_lines.append(m.group(1).rstrip())
            continue
        if only_stmt.match(line.strip()):
            out_lines.append("")
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _strip_code_line_runs(text: str, *, min_code_lines: int = 3) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not _line_looks_like_code(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        run_start = i
        code_n = 0
        saw_def_or_class = False
        while i < len(lines):
            L = lines[i]
            if not L.strip():
                i += 1
                continue
            if _line_looks_like_code(L):
                code_n += 1
                ls = L.lstrip()
                if ls.startswith("def ") or ls.startswith("class ") or ls.startswith("async def "):
                    saw_def_or_class = True
                i += 1
            else:
                break
        drop = code_n >= min_code_lines or (saw_def_or_class and code_n >= 2)
        if not drop:
            out.extend(lines[run_start:i])
    return "\n".join(out)


def sanitize_extracted_article_body(text: str) -> str:
    """
    Drop tutorial code dumps and widget phrases from RSS/newspaper plain text.

    Intended for trend/summary pipelines — not a perfect AST parse; errs toward
    removing obvious code runs and known UI strings.
    """
    if not text or not text.strip():
        return (text or "").strip()

    t = text
    t = _COPY_CODE_CHUNK.sub(" ", t)
    t = _COPY_CODE_SHORT.sub(" ", t)
    t = _FULL_CODES.sub(" ", t)
    t = _ALSO_FOLLOW_TAIL.sub("", t)
    t = _THE_POST_TAIL.sub("", t)
    t = _THE_POST_INLINE.sub("", t)

    t = _scrub_inline_statement_tails(t)
    t = _strip_code_line_runs(t)

    t = re.sub(r"[ \t\f\v]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
