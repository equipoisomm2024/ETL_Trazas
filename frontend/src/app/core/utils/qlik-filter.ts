/**
 * Evaluador de filtros WHERE estilo QlikView (TypeScript).
 *
 * Sintaxis soportada:
 *   WildMatch(@N, 'pat1', 'pat2', ...)   — comodines * y ?, insensible a mayúsculas
 *   AND / OR / NOT
 *   Paréntesis para agrupar
 *
 * Ejemplo:
 *   WildMatch(@12, '*\/S<ATP>*') OR WildMatch(@12, '*\/C<ATP>*')
 */

// ── Tokens ──────────────────────────────────────────────────────────────────

type TokenType =
  | 'WILDMATCH' | 'AND' | 'OR' | 'NOT'
  | 'LPAREN' | 'RPAREN' | 'COMMA'
  | 'FIELD' | 'STRING' | 'EOF';

interface Token { type: TokenType; value: string; }

const TOKEN_PATTERNS: [RegExp, TokenType | null][] = [
  [/^WildMatch\b/i,  'WILDMATCH'],
  [/^AND\b/i,        'AND'],
  [/^OR\b/i,         'OR'],
  [/^NOT\b/i,        'NOT'],
  [/^\(/,            'LPAREN'],
  [/^\)/,            'RPAREN'],
  [/^,/,             'COMMA'],
  [/^@\d+/,          'FIELD'],
  [/^'[^']*'/,       'STRING'],
  [/^\s+/,           null],     // ignorar espacios
];

function tokenize(expr: string): Token[] {
  const tokens: Token[] = [];
  let pos = 0;
  while (pos < expr.length) {
    let matched = false;
    for (const [pattern, ttype] of TOKEN_PATTERNS) {
      const m = expr.slice(pos).match(pattern);
      if (m) {
        if (ttype !== null) tokens.push({ type: ttype, value: m[0] });
        pos += m[0].length;
        matched = true;
        break;
      }
    }
    if (!matched) {
      throw new Error(`Carácter inesperado en posición ${pos}: '${expr[pos]}'`);
    }
  }
  tokens.push({ type: 'EOF', value: '' });
  return tokens;
}

// ── Evaluador ────────────────────────────────────────────────────────────────

export class QlikFilter {
  private tokens: Token[] = [];
  private pos = 0;
  private fields: string[] = [];

  constructor(private readonly expression: string) {}

  /**
   * Evalúa si una línea pasa el filtro.
   * @param linea  línea de texto sin procesar
   * @param sep    separador de campos (por defecto: espacio)
   */
  matches(linea: string, sep = ' '): boolean {
    if (!this.expression.trim()) return true;
    this.fields = this.split(linea, sep);
    this.tokens = tokenize(this.expression);
    this.pos = 0;
    return this.parseOr();
  }

  /** Devuelve null si la expresión es válida, o el mensaje de error. */
  static validate(expression: string): string | null {
    if (!expression.trim()) return null;
    try {
      new QlikFilter(expression).matches('a b c d e f g h i j k l m n o p q r s t u v w x y z');
      return null;
    } catch (e: any) {
      return e.message ?? String(e);
    }
  }

  // ── Parser recursivo descendente ──────────────────────────────────────────

  private peek(): Token { return this.tokens[this.pos]; }

  private consume(expected?: TokenType): Token {
    const tok = this.tokens[this.pos];
    if (expected && tok.type !== expected) {
      throw new Error(`Se esperaba ${expected}, se obtuvo ${tok.type} ('${tok.value}')`);
    }
    this.pos++;
    return tok;
  }

  private parseOr(): boolean {
    let left = this.parseAnd();
    while (this.peek().type === 'OR') {
      this.consume('OR');
      left = left || this.parseAnd();
    }
    return left;
  }

  private parseAnd(): boolean {
    let left = this.parseNot();
    while (this.peek().type === 'AND') {
      this.consume('AND');
      left = left && this.parseNot();
    }
    return left;
  }

  private parseNot(): boolean {
    if (this.peek().type === 'NOT') {
      this.consume('NOT');
      return !this.parseNot();
    }
    return this.parsePrimary();
  }

  private parsePrimary(): boolean {
    if (this.peek().type === 'LPAREN') {
      this.consume('LPAREN');
      const result = this.parseOr();
      this.consume('RPAREN');
      return result;
    }
    if (this.peek().type === 'WILDMATCH') {
      return this.parseWildMatch();
    }
    throw new Error(`Función o expresión no reconocida: '${this.peek().value}'`);
  }

  private parseWildMatch(): boolean {
    this.consume('WILDMATCH');
    this.consume('LPAREN');

    const fieldTok = this.consume('FIELD');
    const idx = parseInt(fieldTok.value.slice(1), 10) - 1;  // @1 → 0
    const value = (idx >= 0 && idx < this.fields.length) ? this.fields[idx] : '';

    const patterns: string[] = [];
    this.consume('COMMA');
    patterns.push(this.readString());
    while (this.peek().type === 'COMMA') {
      this.consume('COMMA');
      patterns.push(this.readString());
    }
    this.consume('RPAREN');

    return this.wildMatch(value, patterns);
  }

  private readString(): string {
    const tok = this.consume('STRING');
    return tok.value.slice(1, -1);   // quitar comillas simples
  }

  // ── WildMatch ─────────────────────────────────────────────────────────────

  private wildMatch(value: string, patterns: string[]): boolean {
    const v = value.toLowerCase();
    for (const pattern of patterns) {
      if (this.fnmatch(v, pattern.toLowerCase())) return true;
    }
    return false;
  }

  /** Convierte patrón de comodines al estilo shell a RegExp y comprueba. */
  private fnmatch(str: string, pattern: string): boolean {
    // Escapar caracteres especiales regex, luego sustituir * y ?
    const regexStr = pattern
      .replace(/[.+^${}()|[\]\\]/g, '\\$&')  // escapar especiales (excepto * y ?)
      .replace(/\*/g, '.*')
      .replace(/\?/g, '.');
    return new RegExp(`^${regexStr}$`).test(str);
  }

  // ── Split ─────────────────────────────────────────────────────────────────

  private split(linea: string, sep: string): string[] {
    if (!sep || sep === ' ' || sep === '\t') {
      return linea.trim().split(/\s+/).filter(t => t.length > 0);
    }
    return linea.split(sep).map(t => t.trim()).filter(t => t.length > 0);
  }
}
