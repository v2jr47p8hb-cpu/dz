"""MathML (ФИПИ, префикс m:) → LaTeX для KaTeX. Незнакомые теги отмечаются в UNKNOWN."""
import re
from bs4 import NavigableString, Tag

UNKNOWN = set()

MO = {
    "−": "-", "–": "-", "⋅": r"\cdot ", "·": r"\cdot ", "×": r"\times ", "÷": ":",
    "≤": r"\le ", "≥": r"\ge ", "≠": r"\ne ", "≈": r"\approx ", "∠": r"\angle ",
    "°": r"^{\circ}", "∪": r"\cup ", "∩": r"\cap ", "∈": r"\in ", "∉": r"\notin ",
    "∞": r"\infty ", "⊥": r"\perp ", "∥": r"\parallel ", "‖": r"\parallel ", "△": r"\triangle ",
    "Δ": r"\triangle ", "∆": r"\triangle ", "±": r"\pm ", "∓": r"\mp ", "→": r"\to ",
    "⇒": r"\Rightarrow ", "⇔": r"\Leftrightarrow ", "…": r"\ldots ", "⋯": r"\cdots ",
    "%": r"\%", "{": r"\{", "}": r"\}", "#": r"\#", "&": r"\&", "—": r"\text{—}", "′": "'",
    "⁡": "", "⁢": "", "⁣": "", "​": "", "∅": r"\varnothing ", "⊂": r"\subset ",
    "≡": r"\equiv ", "∼": r"\sim ", "≅": r"\cong ", "∘": r"\circ ", "√": r"\surd ",
    "‖": r"\|", "〈": r"\langle ", "〉": r"\rangle ", "⟨": r"\langle ", "⟩": r"\rangle ",
    "⁄": "/", "∕": "/", "¬": r"\neg ", "∧": r"\wedge ", "∨": r"\vee ",
}
GREEK = {
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta", "ε": r"\varepsilon", "φ": r"\varphi",
    "π": r"\pi", "ρ": r"\rho", "σ": r"\sigma", "τ": r"\tau", "ω": r"\omega", "λ": r"\lambda", "μ": r"\mu",
    "θ": r"\theta", "ν": r"\nu", "η": r"\eta", "ξ": r"\xi", "χ": r"\chi", "ψ": r"\psi", "ζ": r"\zeta",
    "κ": r"\kappa", "Ω": r"\Omega", "Φ": r"\Phi", "Σ": r"\Sigma", "Π": r"\Pi", "Γ": r"\Gamma", "Λ": r"\Lambda",
}
FUNCS = {"sin", "cos", "tg", "ctg", "tan", "cot", "log", "lg", "ln", "arcsin", "arccos", "arctg", "min", "max", "lim"}
SPACES = "             "


def is_cyr(s):
    return any("Ѐ" <= c <= "ӿ" for c in s)


def esc_text(s):
    return s.replace("\\", r"\backslash ").replace("{", r"\{").replace("}", r"\}").replace("%", r"\%") \
        .replace("#", r"\#").replace("&", r"\&").replace("_", r"\_").replace("^", r"\^{}").replace("$", r"\$")


def grp(s):
    s = s.strip()
    return "{" + s + "}"


def kids(t):
    return [c for c in t.children if isinstance(c, Tag)]


def sym(ch):
    if ch in MO:
        return MO[ch]
    if ch in GREEK:
        return GREEK[ch] + " "
    if ch in SPACES:
        return " "
    return ch


def conv_text(s, mode):
    s = s.replace("­", "")
    if mode == "mi":
        st = s.strip()
        if st in FUNCS:
            return r"\operatorname{" + st + "} " if st in ("tg", "ctg", "arctg", "lg") else "\\" + st + " "
        if st in GREEK:
            return GREEK[st] + " "
        if is_cyr(st):
            return r"\text{" + esc_text(st) + "}"
        return "".join(sym(c) for c in st)
    if mode == "mn":
        st = s.strip().replace(" ", r"\ ").replace(" ", r"\ ")
        return st.replace(",", "{,}")
    if mode == "mo":
        st = s.strip()
        if st in FUNCS:
            return "\\" + st + " " if st not in ("tg", "ctg") else r"\operatorname{" + st + "} "
        if len(st) > 1 and is_cyr(st):
            return r"\text{" + esc_text(st) + "}"
        return "".join(sym(c) for c in st) if st else ""
    if mode == "mtext":
        s = s.replace("\u200b", "").replace("\u2060", "")
        if s.strip() in GREEK:
            return GREEK[s.strip()] + " "
        if s.strip(SPACES) == "":
            return r"\," if s else ""
        return r"\text{" + esc_text(s.replace(" ", " ")) + "}"
    return s


def conv(t):
    if isinstance(t, NavigableString):
        return ""  # пробелы между тегами MathML
    n = t.name.split(":")[-1]
    ch = kids(t)
    if n in ("math", "mstyle", "semantics", "mrow", "mpadded", "mphantom_", "menclose", "annotation-xml"):
        return "".join(conv(c) for c in ch)
    if n == "annotation":
        return ""
    if n in ("mi", "mn", "mo", "mtext", "ms"):
        return conv_text(t.get_text(), "mtext" if n == "ms" else n)
    if n == "mspace":
        return r"\ "
    if n == "msup":
        b, e = (ch + [None, None])[:2]
        return grp(conv(b)) + "^" + grp(conv(e)) if e is not None else conv(b)
    if n == "msub":
        b, e = (ch + [None, None])[:2]
        return grp(conv(b)) + "_" + grp(conv(e)) if e is not None else conv(b)
    if n == "msubsup":
        b, lo, hi = (ch + [None, None, None])[:3]
        s = grp(conv(b))
        lo_s = conv(lo) if lo is not None else ""
        hi_s = conv(hi) if hi is not None else ""
        if lo_s.strip():
            s += "_" + grp(lo_s)
        if hi_s.strip():
            s += "^" + grp(hi_s)
        return s if (lo_s.strip() or hi_s.strip()) else conv(b)
    if n == "mfrac":
        a, b = (ch + [None, None])[:2]
        if t.get("linethickness") in ("0", "0px", "0pt"):
            return r"\genfrac{}{}{0pt}{}" + grp(conv(a)) + grp(conv(b))
        return r"\frac" + grp(conv(a)) + grp(conv(b))
    if n == "msqrt":
        return r"\sqrt" + grp("".join(conv(c) for c in ch))
    if n == "mroot":
        a, b = (ch + [None, None])[:2]
        return r"\sqrt[" + conv(b) + "]" + grp(conv(a))
    if n in ("mover", "munder", "munderover"):
        parts = [conv(c) for c in ch]
        base = parts[0] if parts else ""
        if n == "mover" and len(parts) > 1:
            acc = ch[1].get_text().strip()
            if acc in ("¯", "‾", "―", "_", "̅", "-", "−"):
                return r"\overline" + grp(base)
            if acc in ("→", "⟶", "⃗"):
                return r"\overrightarrow" + grp(base)
            if acc in ("^", "ˆ", "̂"):
                return r"\hat" + grp(base)
            if acc in ("⌒", "⌢", "◠"):
                return r"\overset{\frown}" + grp(base)
            return r"\overset" + grp(parts[1]) + grp(base)
        if n == "munder" and len(parts) > 1:
            return r"\underset" + grp(parts[1]) + grp(base)
        if n == "munderover":
            s = base
            if len(parts) > 1 and parts[1].strip():
                s = r"\underset" + grp(parts[1]) + grp(s)
            if len(parts) > 2 and parts[2].strip():
                s = r"\overset" + grp(parts[2]) + grp(s)
            return s
        return base
    if n == "mfenced":
        op = t.get("open", "(")
        cl = t.get("close", ")")
        sep = t.get("separators", ",")
        inner = []
        for i, c in enumerate(ch):
            if i:
                inner.append(sep[min(i - 1, len(sep) - 1)] if sep else "")
            inner.append(conv(c))
        d = lambda x: "." if not x else (r"\{" if x == "{" else r"\}" if x == "}" else x)
        return r"\left" + d(op) + " " + "".join(inner) + r" \right" + d(cl)
    if n == "mtable":
        rows = []
        for tr in ch:
            cells = [conv(td) for td in kids(tr)] if tr.name.endswith("mtr") or tr.name.endswith("mlabeledtr") else [conv(tr)]
            rows.append(" & ".join(cells))
        ncol = max((len(kids(tr)) for tr in ch), default=1) or 1
        return r"\begin{array}{" + "l" * ncol + "}" + r" \\ ".join(rows) + r"\end{array}"
    if n in ("mtr", "mtd", "mlabeledtr"):
        return "".join(conv(c) for c in ch)
    if n == "mphantom":
        return r"\phantom" + grp("".join(conv(c) for c in ch))
    UNKNOWN.add(n)
    return "".join(conv(c) for c in ch)


def to_latex(math_tag):
    s = conv(math_tag)
    # склейка \left( … \right) из отдельных mo не нужна; чистим лишние пробелы
    s = " ".join(s.split())
    return s


PLAIN = re.compile(r"^(?:\\text\{([^{}\\]*)\}|\s|\\,)+$")


def plain_or_none(tex):
    """Формула целиком из \\text{…} (тире, слова) — отдаём обычным текстом."""
    if PLAIN.match(tex):
        return "".join(re.findall(r"\\text\{([^{}\\]*)\}", tex))
    return None
