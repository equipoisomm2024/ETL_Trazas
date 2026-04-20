"""
Evaluador de filtros WHERE estilo QlikView.

Sintaxis soportada:
  - WildMatch(@N, 'pat1', 'pat2', ...)  — comodines * y ?, insensible a mayúsculas
  - AND, OR, NOT  (case-insensitive)
  - Paréntesis para agrupar

Ejemplo:
    WildMatch(@12, '*/S<ATP>*') OR WildMatch(@12, '*/C<ATP>*')
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from typing import List, Optional


# ── Tokenizer ──────────────────────────────────────────────────────────────

TK_WILDMATCH = "WILDMATCH"
TK_AND       = "AND"
TK_OR        = "OR"
TK_NOT       = "NOT"
TK_LPAREN    = "LPAREN"
TK_RPAREN    = "RPAREN"
TK_COMMA     = "COMMA"
TK_FIELD     = "FIELD"   # @N
TK_STRING    = "STRING"  # 'literal'
TK_EOF       = "EOF"


@dataclass
class _Token:
    type: str
    value: str


_TOKEN_PATTERNS: list[tuple[re.Pattern, str | None]] = [
    (re.compile(r"(?i)\bWildMatch\b"), TK_WILDMATCH),
    (re.compile(r"(?i)\bAND\b"),       TK_AND),
    (re.compile(r"(?i)\bOR\b"),        TK_OR),
    (re.compile(r"(?i)\bNOT\b"),       TK_NOT),
    (re.compile(r"\("),                TK_LPAREN),
    (re.compile(r"\)"),                TK_RPAREN),
    (re.compile(r","),                 TK_COMMA),
    (re.compile(r"@\d+"),             TK_FIELD),
    (re.compile(r"'[^']*'"),           TK_STRING),
    (re.compile(r"\s+"),               None),    # ignorar espacios
]


def _tokenize(expr: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    while pos < len(expr):
        for pattern, ttype in _TOKEN_PATTERNS:
            m = pattern.match(expr, pos)
            if m:
                if ttype is not None:
                    tokens.append(_Token(ttype, m.group()))
                pos = m.end()
                break
        else:
            raise ValueError(
                f"Carácter inesperado en posición {pos}: '{expr[pos]}'"
            )
    tokens.append(_Token(TK_EOF, ""))
    return tokens


# ── Evaluador ──────────────────────────────────────────────────────────────

class QlikWhereEvaluator:
    """
    Evalúa una expresión WHERE estilo QlikView contra una fila de campos.

    Los campos se referencian como @1, @2, … (índice 1-based).
    El separador usado para dividir la línea en campos debe pasarse al
    construir el evaluador (por defecto: espacio/tabulador).

    Uso:
        ev = QlikWhereEvaluator("WildMatch(@12, '*/S<ATP>*') OR WildMatch(@12, '*/C<ATP>*')")
        if ev.matches(linea_raw, separador=';'):
            ...
    """

    def __init__(self, expression: str, separador: str = " ") -> None:
        self._expression = expression.strip()
        self._separador = separador
        # Pre-compilar tokens; si la expresión es vacía, matches() devuelve True siempre
        self._tokens: list[_Token] = _tokenize(self._expression) if self._expression else []
        self._pos = 0
        self._fields: list[str] = []

    # ── API pública ────────────────────────────────────────────────────────

    def matches(self, linea: str, separador: str | None = None) -> bool:
        """Devuelve True si la línea cumple el filtro (o si no hay filtro)."""
        if not self._expression:
            return True
        sep = separador if separador is not None else self._separador
        self._fields = self._split(linea, sep)
        self._tokens = _tokenize(self._expression)
        self._pos = 0
        return self._parse_or()

    @classmethod
    def validate(cls, expression: str, separador: str = " ") -> Optional[str]:
        """
        Valida la expresión sintácticamente.
        Devuelve None si es válida, o el mensaje de error si no lo es.
        """
        if not expression or not expression.strip():
            return None
        try:
            ev = cls(expression, separador)
            ev.matches("a b c d e f g h i j k l m n o p q r s t u v w x y z", separador=" ")
            return None
        except Exception as exc:
            return str(exc)

    # ── Parser recursivo descendente ───────────────────────────────────────

    def _peek(self) -> _Token:
        return self._tokens[self._pos]

    def _consume(self, expected: str | None = None) -> _Token:
        tok = self._tokens[self._pos]
        if expected and tok.type != expected:
            raise ValueError(
                f"Se esperaba {expected}, se obtuvo {tok.type} ('{tok.value}')"
            )
        self._pos += 1
        return tok

    def _parse_or(self) -> bool:
        left = self._parse_and()
        while self._peek().type == TK_OR:
            self._consume(TK_OR)
            right = self._parse_and()
            left = left or right
        return left

    def _parse_and(self) -> bool:
        left = self._parse_not()
        while self._peek().type == TK_AND:
            self._consume(TK_AND)
            right = self._parse_not()
            left = left and right
        return left

    def _parse_not(self) -> bool:
        if self._peek().type == TK_NOT:
            self._consume(TK_NOT)
            return not self._parse_not()
        return self._parse_primary()

    def _parse_primary(self) -> bool:
        if self._peek().type == TK_LPAREN:
            self._consume(TK_LPAREN)
            result = self._parse_or()
            self._consume(TK_RPAREN)
            return result
        if self._peek().type == TK_WILDMATCH:
            return self._parse_wildmatch()
        raise ValueError(
            f"Función o expresión no reconocida: '{self._peek().value}'"
        )

    def _parse_wildmatch(self) -> bool:
        self._consume(TK_WILDMATCH)
        self._consume(TK_LPAREN)

        field_tok = self._consume(TK_FIELD)
        idx = int(field_tok.value[1:]) - 1          # @1 → índice 0
        value = self._fields[idx] if 0 <= idx < len(self._fields) else ""

        patterns: list[str] = []
        self._consume(TK_COMMA)
        patterns.append(self._read_string())
        while self._peek().type == TK_COMMA:
            self._consume(TK_COMMA)
            patterns.append(self._read_string())
        self._consume(TK_RPAREN)

        return self._wildmatch(value, patterns)

    def _read_string(self) -> str:
        tok = self._consume(TK_STRING)
        return tok.value[1:-1]   # quitar comillas simples

    # ── Funciones QlikView ─────────────────────────────────────────────────

    @staticmethod
    def _wildmatch(value: str, patterns: list[str]) -> bool:
        """
        Equivalente a QlikView WildMatch():
        - Case-insensitive
        - * = cualquier secuencia de caracteres
        - ? = un solo carácter
        Devuelve True si alguno de los patrones coincide.
        """
        v = value.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(v, pattern.lower()):
                return True
        return False

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _split(linea: str, sep: str) -> list[str]:
        """Divide la línea en campos usando el separador indicado."""
        if not sep or sep in (" ", "\t"):
            return linea.split()          # absorbe múltiples espacios/tabs
        return [t.strip() for t in linea.split(sep)]
