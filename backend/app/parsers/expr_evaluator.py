"""Evaluador seguro de expresiones para campos calculados.

Soporta:
  - Referencias a tokens por posición:  @1, @2, @3 …
  - Referencias a campos ya extraídos:  nombre_campo
  - Operadores aritméticos: + - * / % **
  - Concatenación de cadenas con +
  - Funciones básicas: int(), float(), str()
  - Literales numéricos y de cadena

Ejemplo:
  @1 * 10
  'prefijo_' + @2
  int(@3) / 100
  @1 + '-' + @2
"""

import ast
import operator as _op
import re

_OPERADORES = {
    ast.Add:  _op.add,
    ast.Sub:  _op.sub,
    ast.Mult: _op.mul,
    ast.Div:  _op.truediv,
    ast.Mod:  _op.mod,
    ast.Pow:  _op.pow,
    ast.USub: _op.neg,
    ast.UAdd: _op.pos,
}

_FUNCIONES_PERMITIDAS = {"int": int, "float": float, "str": str}

_RE_TOKEN = re.compile(r"@(\d+)")


def _nodo(node, ctx: dict):
    """Evalúa recursivamente un nodo AST en el contexto dado."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ctx:
            return ctx[node.id]
        raise ValueError(f"Variable no definida: '{node.id}'")
    if isinstance(node, ast.BinOp):
        fn = _OPERADORES.get(type(node.op))
        if fn is None:
            raise ValueError(f"Operador no soportado: {type(node.op).__name__}")
        return fn(_nodo(node.left, ctx), _nodo(node.right, ctx))
    if isinstance(node, ast.UnaryOp):
        fn = _OPERADORES.get(type(node.op))
        if fn is None:
            raise ValueError(f"Operador no soportado: {type(node.op).__name__}")
        return fn(_nodo(node.operand, ctx))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _FUNCIONES_PERMITIDAS:
            fn = _FUNCIONES_PERMITIDAS[node.func.id]
            args = [_nodo(a, ctx) for a in node.args]
            return fn(*args)
        raise ValueError(f"Función no permitida: '{ast.dump(node.func)}'")
    raise ValueError(f"Expresión no soportada: {type(node).__name__}")


def evaluar(expresion: str, tokens: list[str], datos_extraidos: dict) -> object:
    """Evalúa *expresion* reemplazando @N por el token N-ésimo (1-based).

    Args:
        expresion:       La expresión a evaluar, p.ej. ``"@1 * 10"``.
        tokens:          Lista de tokens obtenidos al dividir la línea por el separador.
        datos_extraidos: Campos ya extraídos en esta línea (dict campo_bd → valor).

    Returns:
        El resultado calculado (str, int, float, …).

    Raises:
        ValueError: si la expresión contiene construcciones no permitidas o la evaluación falla.
    """
    ctx: dict = {}

    def _sustituir(m: re.Match) -> str:
        n = int(m.group(1))
        var = f"_t{n}"
        ctx[var] = tokens[n - 1] if 1 <= n <= len(tokens) else ""
        return var

    expr_sustituida = _RE_TOKEN.sub(_sustituir, expresion)

    # Añadir datos ya extraídos como variables del contexto
    for k, v in datos_extraidos.items():
        if isinstance(k, str) and k.isidentifier():
            ctx.setdefault(k, v)

    try:
        tree = ast.parse(expr_sustituida, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Sintaxis inválida en expresión '{expresion}': {exc}") from exc

    return _nodo(tree.body, ctx)
