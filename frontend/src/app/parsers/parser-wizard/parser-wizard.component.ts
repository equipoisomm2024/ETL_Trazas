import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ParsersService } from '../../core/api/parsers.service';
import {
  FilesService,
  ContenidoDirectorio,
  EntradaDirectorio,
  LineaPreview,
} from '../../core/api/files.service';
import { TipoDato, TIPOS_DATO } from '../../core/models';
import { QlikFilter } from '../../core/utils/qlik-filter';

export interface CampoWizard {
  pos: number;
  muestra: string;
  incluir: boolean;
  nombre: string;
  campoBd: string;
  tipo: TipoDato;
  formato: string;
  longitud: number | null;
  grupoUnion: number | null;
}

@Component({
  selector: 'app-parser-wizard',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './parser-wizard.component.html',
})
export class ParserWizardComponent implements OnInit {
  private readonly parsersService = inject(ParsersService);
  private readonly filesService = inject(FilesService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);

  readonly tiposDato = TIPOS_DATO;
  readonly tablaDestinos = ['t_errores', 't_metricas', 't_eventos'];

  // ── Wizard step ──────────────────────────────────────────────────────────
  paso = signal<1 | 2 | 3>(1);

  // ── Step 1: datos básicos ────────────────────────────────────────────────
  form: FormGroup = this.fb.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    descripcion: [''],
    tabla_destino: [''],
    activo: [true],
  });

  // ── Step 3: tabla destino ────────────────────────────────────────────────
  modoTabla = signal<'existente' | 'nueva'>('existente');
  tablaNueva = signal('');

  // ── Step 2: explorador de ficheros ───────────────────────────────────────
  mostrarExplorador = signal(false);
  explorador = signal<ContenidoDirectorio | null>(null);
  exploradorCargando = signal(false);
  exploradorError = signal<string | null>(null);
  exploradorSeleccionado = signal<string | null>(null);
  exploradorRutaManual = signal('');

  rutaFichero = signal<string | null>(null);
  rutaDirectorio = signal<string | null>(null);

  // ── Step 2: filtro WHERE ─────────────────────────────────────────────────
  filtroWhere = signal('');
  filtroError = signal<string | null>(null);

  // ── Step 2: exploración del fichero ─────────────────────────────────────
  ficheroLineas = signal<LineaPreview[]>([]);
  ficheroError = signal<string | null>(null);
  ficheroCargando = signal(false);

  lineaSeleccionada = signal<LineaPreview | null>(null);

  // ── Step 2: separador de campos ──────────────────────────────────────────
  readonly opcionesSeparador = [
    { label: 'Tabulación', value: 'tab' },
    { label: 'Punto y coma', value: 'punto_coma' },
    { label: 'Coma', value: 'coma' },
    { label: 'Espacio', value: 'espacio' },
    { label: 'Otro', value: 'otro' },
  ];
  modoSeparador = signal<string>('espacio');
  separadorPersonalizado = signal<string>('');
  delimitador = computed(() => {
    switch (this.modoSeparador()) {
      case 'tab':        return '\t';
      case 'punto_coma': return ';';
      case 'coma':       return ',';
      case 'espacio':    return ' ';
      case 'otro':       return this.separadorPersonalizado();
      default:           return ' ';
    }
  });

  // ── Step 2: configuración de campos ──────────────────────────────────────
  campos = signal<CampoWizard[]>([]);

  // ── Step 2: unión de campos ───────────────────────────────────────────────
  columnasSeleccionadasUnir = signal<Set<number>>(new Set());
  private nextGrupoId = signal(0);

  // ── Step 2: orden visual de columnas (drag & drop) ────────────────────────
  columnDisplayOrder = signal<number[]>([]);
  dragSourceCol  = signal<number | null>(null);  // solo para CSS
  dragOverCol    = signal<number | null>(null);   // solo para CSS
  draggingActive = signal(false);                 // activa pointer-events:none en hijos de th
  private _dragSourceN: number | null = null;    // fuente de verdad del drag (variable plana)

  // ── Step 3: guardar ──────────────────────────────────────────────────────
  guardando = signal(false);
  errorGuardar = signal<string | null>(null);

  // ── Computed ─────────────────────────────────────────────────────────────

  lineasVista = computed(() => {
    const sep  = this.delimitador();
    const expr = this.filtroWhere().trim();
    const filter = expr && !this.filtroError() ? new QlikFilter(expr) : null;

    return this.ficheroLineas().slice(0, 500).map(l => {
      const tokens = this.tokenizar(l.contenido, sep);
      let pasaFiltro = true;
      if (filter) {
        try { pasaFiltro = filter.matches(l.contenido, sep); }
        catch { pasaFiltro = true; }
      }
      return { linea: l, tokens, pasaFiltro };
    });
  });

  ocultarExcluidas = signal(true);
  columnasExcluidas = signal<Set<number>>(new Set());
  ocultarColumnasDescartadas = signal(false);

  lineasMostradas = computed(() => {
    const items = this.lineasVista();
    return this.ocultarExcluidas() ? items.filter(item => item.pasaFiltro) : items;
  });

  // Combina filas + columnas en un único computed para garantizar que el @for de datos
  // se re-renderiza cuando cambian las columnas (grupos) aunque las filas no cambien.
  filasParaTabla = computed(() => ({
    cols: this.encabezadosVisibles(),
    filas: this.lineasMostradas(),
  }));

  maxTokens = computed(() =>
    this.lineasVista()
      .filter(item => item.pasaFiltro)
      .reduce((max, item) => Math.max(max, item.tokens.length), 0)
  );

  encabezados = computed(() =>
    Array.from({ length: this.maxTokens() }, (_, i) => i + 1)
  );

  // Columnas visibles: respeta el orden visual definido por drag & drop.
  // Los miembros contiguos del mismo grupo se fusionan en una única entrada con positions=[p1,p2,...].
  encabezadosVisibles = computed((): { n: number; descartada: boolean; grupoId: number | null; positions: number[] }[] => {
    const excluidas = this.columnasExcluidas();
    const cs        = this.campos();
    const order     = this.columnDisplayOrder();
    const nMax      = this.maxTokens();

    const effectiveOrder = order.length > 0
      ? order
      : Array.from({ length: nMax }, (_, i) => i + 1);

    const cols: { n: number; descartada: boolean; grupoId: number | null; positions: number[] }[] = [];
    let i = 0;
    while (i < effectiveOrder.length) {
      const n   = effectiveOrder[i];
      const pos = n - 1;
      const descartada = excluidas.has(n);
      if (this.ocultarColumnasDescartadas() && descartada) { i++; continue; }

      const campo   = cs.find(c => c.pos === pos);
      const grupoId = campo?.grupoUnion ?? null;

      if (grupoId !== null) {
        // Recoger miembros contiguos del mismo grupo
        const positions: number[] = [pos];
        let j = i + 1;
        while (j < effectiveOrder.length) {
          const nextN   = effectiveOrder[j];
          const nextPos = nextN - 1;
          if (cs.find(c => c.pos === nextPos)?.grupoUnion === grupoId) {
            positions.push(nextPos);
            j++;
          } else break;
        }

        if (positions.length >= 2) {
          // Cabecera única para el grupo
          const allDesc = positions.every(p => excluidas.has(p + 1));
          if (!(this.ocultarColumnasDescartadas() && allDesc)) {
            cols.push({ n, descartada: allDesc, grupoId, positions });
          }
          i = j;
        } else {
          // Miembro aislado (no contiguo): mostrar individualmente con badge de grupo
          cols.push({ n, descartada, grupoId, positions: [pos] });
          i++;
        }
      } else {
        cols.push({ n, descartada, grupoId: null, positions: [pos] });
        i++;
      }
    }
    return cols;
  });

  regexGenerado = computed(() => this.calcRegex(this.campos(), this.columnasExcluidas()));
  camposGenerados = computed(() => this.calcCampos(this.campos(), this.columnasExcluidas()));

  tablaEfectiva = computed(() =>
    this.modoTabla() === 'nueva'
      ? this.tablaNueva().trim()
      : this.form.value.tabla_destino
  );

  puedeIrPaso2 = computed(() => this.form.get('nombre')!.valid);

  puedeGuardar = computed(() =>
    this.puedeIrPaso3() && this.tablaEfectiva().length > 0
  );
  puedeIrPaso3 = computed(() =>
    this.campos().length > 0 &&
    this.campos().some(c => c.campoBd.trim())
  );

  filasEfectivas = computed(() => {
    const cs = this.campos();
    const excluidas = this.columnasExcluidas();
    const processedGrupos = new Set<number>();
    const filas: { indices: number[]; muestras: string[]; lider: CampoWizard }[] = [];

    for (let i = 0; i < cs.length; i++) {
      if (excluidas.has(cs[i].pos + 1)) continue;

      if (cs[i].grupoUnion !== null) {
        const grupoId = cs[i].grupoUnion!;
        if (processedGrupos.has(grupoId)) continue;
        processedGrupos.add(grupoId);
        const members = cs
          .map((c, idx) => ({ c, idx }))
          .filter(({ c }) => c.grupoUnion === grupoId && !excluidas.has(c.pos + 1))
          .sort((a, b) => a.c.pos - b.c.pos);
        filas.push({
          indices: members.map(m => m.idx),
          muestras: members.map(m => m.c.muestra),
          lider: members[0].c,
        });
      } else {
        filas.push({ indices: [i], muestras: [cs[i].muestra], lider: cs[i] });
      }
    }
    return filas;
  });

  ngOnInit(): void {}

  // ── Navegación de pasos ──────────────────────────────────────────────────
  irPaso(n: 1 | 2 | 3): void {
    if (n === 2 && !this.puedeIrPaso2()) { this.form.markAllAsTouched(); return; }
    if (n === 3 && !this.puedeIrPaso3()) return;
    this.paso.set(n);
  }

  // ── Explorador de ficheros ───────────────────────────────────────────────
  abrirExplorador(): void {
    this.mostrarExplorador.set(true);
    this.exploradorSeleccionado.set(null);
    this.navegarExplorador(this.rutaDirectorio() ?? '/workspace/proyectos/ETL_Trazas/Pruebas/P1');
  }

  navegarExplorador(path: string): void {
    if (!path.trim()) return;
    this.exploradorCargando.set(true);
    this.exploradorError.set(null);
    this.exploradorSeleccionado.set(null);
    this.filesService.browse(path).subscribe({
      next: (data) => {
        this.explorador.set(data);
        this.exploradorRutaManual.set(data.ruta_actual);
        this.exploradorCargando.set(false);
      },
      error: (e) => {
        this.exploradorError.set(e.error?.detail ?? 'Error al explorar el directorio.');
        this.exploradorCargando.set(false);
      },
    });
  }

  seleccionarEntrada(entrada: EntradaDirectorio): void {
    if (entrada.es_directorio) {
      this.navegarExplorador(entrada.ruta);
    } else {
      this.exploradorSeleccionado.set(
        this.exploradorSeleccionado() === entrada.ruta ? null : entrada.ruta
      );
    }
  }

  confirmarSeleccion(): void {
    const fichero = this.exploradorSeleccionado();
    const dir = this.explorador()?.ruta_actual;
    if (!fichero || !dir) return;
    this.rutaFichero.set(fichero);
    this.rutaDirectorio.set(dir);
    this.mostrarExplorador.set(false);
    this.ficheroLineas.set([]);
    this.lineaSeleccionada.set(null);
    this.campos.set([]);
    this.ficheroError.set(null);
    this.columnasExcluidas.set(new Set());
    this.columnasSeleccionadasUnir.set(new Set());
    this.columnDisplayOrder.set([]);
    this.cargarFichero(fichero);
  }

  excluirColumna(n: number): void {
    this.columnasExcluidas.update(s => new Set([...s, n]));
  }

  restaurarColumna(n: number): void {
    this.columnasExcluidas.update(s => { const next = new Set(s); next.delete(n); return next; });
  }

  restaurarColumnas(): void {
    this.columnasExcluidas.set(new Set());
  }

  onRutaManualKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') this.navegarExplorador(this.exploradorRutaManual());
  }

  // ── Carga y exploración del fichero ─────────────────────────────────────
  cargarFichero(ruta: string): void {
    this.ficheroCargando.set(true);
    this.ficheroError.set(null);
    this.filesService.preview({ ruta, delimitador: ' ', num_lineas: 500 }).subscribe({
      next: (data) => {
        this.ficheroLineas.set(data.lineas);
        this.ficheroCargando.set(false);
      },
      error: (e) => {
        this.ficheroError.set(e.error?.detail ?? 'Error al leer el fichero.');
        this.ficheroCargando.set(false);
      },
    });
  }

  onClickLinea(item: { linea: LineaPreview; pasaFiltro: boolean }): void {
    if (item.pasaFiltro) this.seleccionarLinea(item.linea);
  }

  seleccionarLinea(linea: LineaPreview): void {
    this.lineaSeleccionada.set(linea);
    this.construirCampos(linea);
  }

  onModoSeparadorChange(modo: string): void {
    this.modoSeparador.set(modo);
    const linea = this.lineaSeleccionada();
    if (linea) this.construirCampos(linea);
  }

  onSeparadorPersonalizadoChange(valor: string): void {
    this.separadorPersonalizado.set(valor);
    const linea = this.lineaSeleccionada();
    if (linea) this.construirCampos(linea);
  }

  tokenizar(contenido: string, sep: string): string[] {
    if (!sep) return [contenido];
    if (sep === ' ' || sep === '\t') {
      return contenido.split(/\s+/).filter(t => t.length > 0);
    }
    return contenido.split(sep).map(t => t.trim()).filter(t => t.length > 0);
  }

  private construirCampos(linea: LineaPreview): void {
    const tokens = this.tokenizar(linea.contenido, this.delimitador());
    this.construirCamposDesdeTokens(tokens);
  }

  private construirCamposDesdeTokens(tokens: string[]): void {
    // Preservar grupos de unión que el usuario haya definido antes de seleccionar plantilla
    const gruposAnteriores = new Map(this.campos().map(c => [c.pos, c.grupoUnion]));
    this.campos.set(tokens.map((t, i) => ({
      pos: i,
      muestra: t,
      incluir: false,
      nombre: `col_${i + 1}`,
      campoBd: '',
      tipo: 'varchar' as TipoDato,
      formato: '',
      longitud: 100,
      grupoUnion: gruposAnteriores.get(i) ?? null,
    })));
    this.columnasSeleccionadasUnir.set(new Set());
    // Preservar el orden visual si ya fue modificado; si no, inicializar secuencial
    if (this.columnDisplayOrder().length !== tokens.length) {
      this.columnDisplayOrder.set(tokens.map((_, i) => i + 1));
    }
  }

  // ── Unión de campos ───────────────────────────────────────────────────────

  toggleSeleccionUnion(pos: number): void {
    // Si el usuario interactúa con columnas antes de seleccionar línea plantilla,
    // inicializamos campos y columnDisplayOrder con entradas básicas.
    const nMax = this.maxTokens();
    if (this.campos().length === 0 && nMax > 0) {
      this.campos.set(Array.from({ length: nMax }, (_, i) => ({
        pos: i, muestra: '', incluir: false,
        nombre: `col_${i + 1}`, campoBd: '',
        tipo: 'varchar' as TipoDato, formato: '', longitud: 100, grupoUnion: null,
      })));
    }
    if (this.columnDisplayOrder().length === 0 && nMax > 0) {
      this.columnDisplayOrder.set(Array.from({ length: nMax }, (_, i) => i + 1));
    }
    this.columnasSeleccionadasUnir.update(s => {
      const next = new Set(s);
      if (next.has(pos)) next.delete(pos); else next.add(pos);
      return next;
    });
  }

  cancelarSeleccionUnion(): void {
    this.columnasSeleccionadasUnir.set(new Set());
  }

  unirSeleccionadas(): void {
    const selected = this.columnasSeleccionadasUnir();
    if (selected.size < 2) return;
    const grupoId = this.nextGrupoId();
    this.nextGrupoId.update(n => n + 1);
    this.campos.update(cs => cs.map(c =>
      selected.has(c.pos) ? { ...c, grupoUnion: grupoId } : c
    ));

    // Reagrupar columnDisplayOrder para que los miembros queden contiguos
    // (condición necesaria para que encabezadosVisibles los fusione en una cabecera única)
    const selectedNs = [...selected].map(pos => pos + 1);
    this.columnDisplayOrder.update(order => {
      // Preservar el orden relativo de los miembros tal como estaban en el array
      const membersInOrder = order.filter(n => selectedNs.includes(n));
      if (membersInOrder.length < 2) return order;
      // Posición del primer miembro en el orden actual
      const firstIdx = order.indexOf(membersInOrder[0]);
      // Calcular el índice de inserción en el array SIN los miembros
      const withoutMembers = order.filter(n => !selectedNs.includes(n));
      const insertAt = order.slice(0, firstIdx).filter(n => !selectedNs.includes(n)).length;
      withoutMembers.splice(insertAt, 0, ...membersInOrder);
      return withoutMembers;
    });

    this.columnasSeleccionadasUnir.set(new Set());
  }

  deshacerUnion(grupoId: number): void {
    this.campos.update(cs => cs.map(c =>
      c.grupoUnion === grupoId ? { ...c, grupoUnion: null } : c
    ));
  }

  deshacerUnionFila(filaIdx: number): void {
    const fila = this.filasEfectivas()[filaIdx];
    const grupoId = this.campos()[fila.indices[0]].grupoUnion;
    if (grupoId !== null) this.deshacerUnion(grupoId);
  }

  // Devuelve el grupoUnion de un campo por posición, o null
  getGrupoDeColumna(pos: number): number | null {
    return this.campos().find(c => c.pos === pos)?.grupoUnion ?? null;
  }

  // Devuelve etiqueta de los miembros del grupo, ej: "@1+@3"
  getGrupoMiembros(grupoId: number): string {
    return this.campos()
      .filter(c => c.grupoUnion === grupoId)
      .sort((a, b) => a.pos - b.pos)
      .map(c => `@${c.pos + 1}`)
      .join('+');
  }

  getColorGrupo(grupoId: number): number {
    return grupoId % 5;
  }

  // Devuelve "A1", "A2"… para cada grupo, numerados de izquierda a derecha
  getEtiquetaGrupo(grupoId: number): string {
    const orden = new Map<number, number>();
    for (const c of this.campos()) {
      if (c.grupoUnion !== null) {
        const min = orden.get(c.grupoUnion);
        if (min === undefined || c.pos < min) orden.set(c.grupoUnion, c.pos);
      }
    }
    const sorted = [...orden.entries()].sort((a, b) => a[1] - b[1]);
    const idx = sorted.findIndex(([id]) => id === grupoId);
    return idx >= 0 ? `A${idx + 1}` : 'A?';
  }

  // Devuelve true si pos es una columna standalone o el líder (pos más bajo) de su grupo
  isLiderOIndependiente(pos: number): boolean {
    const c = this.campos().find(x => x.pos === pos);
    if (!c) return false;
    if (c.grupoUnion === null) return true;
    const minPos = this.campos()
      .filter(x => x.grupoUnion === c.grupoUnion && !this.columnasExcluidas().has(x.pos + 1))
      .reduce((min, x) => Math.min(min, x.pos), Infinity);
    return minPos === pos;
  }

  // Devuelve el campoBd del líder del grupo (o del propio campo si es standalone)
  getNombreBdDeColumna(pos: number): string {
    const c = this.campos().find(x => x.pos === pos);
    if (!c) return '';
    if (c.grupoUnion === null) return c.campoBd;
    const liderPos = this.campos()
      .filter(x => x.grupoUnion === c.grupoUnion && !this.columnasExcluidas().has(x.pos + 1))
      .reduce((min, x) => x.pos < min.pos ? x : min);
    return liderPos.campoBd;
  }

  // Asigna el nombre BD directamente por posición (usado desde la cabecera de la tabla)
  setNombreBdPorPos(pos: number, value: string): void {
    const idx = this.campos().findIndex(c => c.pos === pos);
    if (idx === -1) return;
    const regexNombre = value.trim()
      ? value.trim().replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '') || `col_${pos + 1}`
      : `col_${pos + 1}`;
    const incluir = value.trim().length > 0;
    this.campos.update(cs => {
      const arr = [...cs];
      arr[idx] = { ...arr[idx], nombre: regexNombre, campoBd: value.trim(), incluir };
      return arr;
    });
  }

  // ── Mutaciones de campos ─────────────────────────────────────────────────
  toggleIncluir(filaIdx: number): void {
    const liderIdx = this.filasEfectivas()[filaIdx].indices[0];
    this.campos.update(cs => {
      const arr = [...cs];
      arr[liderIdx] = { ...arr[liderIdx], incluir: !arr[liderIdx].incluir };
      return arr;
    });
  }

  setCampoNombre(filaIdx: number, value: string): void {
    const liderIdx = this.filasEfectivas()[filaIdx].indices[0];
    const pos = liderIdx;
    const regexNombre = value.trim()
      ? value.trim().replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '') || `col_${pos + 1}`
      : `col_${pos + 1}`;
    const incluir = value.trim().length > 0;
    this.campos.update(cs => {
      const arr = [...cs];
      arr[liderIdx] = { ...arr[liderIdx], nombre: regexNombre, campoBd: value.trim(), incluir };
      return arr;
    });
  }

  setCampo(filaIdx: number, field: keyof CampoWizard, value: any): void {
    const liderIdx = this.filasEfectivas()[filaIdx].indices[0];
    this.campos.update(cs => {
      const arr = [...cs];
      arr[liderIdx] = { ...arr[liderIdx], [field]: value };
      return arr;
    });
  }

  etiquetaPosicion(indices: number[]): string {
    const cs = this.campos();
    const lider = cs[indices[0]];
    if (lider.grupoUnion !== null) return this.getEtiquetaGrupo(lider.grupoUnion);
    return `@${lider.pos + 1}`;
  }

  // ── Helpers de contiguidad ────────────────────────────────────────────────
  private sonContiguas(positions: number[]): boolean {
    const sorted = [...positions].sort((a, b) => a - b);
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i] !== sorted[i - 1] + 1) return false;
    }
    return true;
  }

  // ── Generación de regex y campos ─────────────────────────────────────────
  private calcRegex(campos: CampoWizard[], excluidas = new Set<number>()): string {
    if (campos.length === 0) return '';

    // Mapa grupoId → posiciones activas ordenadas
    const grupoPos = new Map<number, number[]>();
    for (const c of campos) {
      if (c.grupoUnion !== null && !excluidas.has(c.pos + 1)) {
        if (!grupoPos.has(c.grupoUnion)) grupoPos.set(c.grupoUnion, []);
        grupoPos.get(c.grupoUnion)!.push(c.pos);
      }
    }
    for (const [id, pos] of grupoPos) grupoPos.set(id, pos.sort((a, b) => a - b));

    const partes: string[] = [];
    const grupoFragIdx = new Map<number, number>();

    for (const c of campos) {
      const excluida = excluidas.has(c.pos + 1);

      if (excluida) {
        partes.push('\\S+');
        continue;
      }

      if (c.grupoUnion === null) {
        partes.push(c.campoBd.trim() ? `(?P<${c.nombre}>\\S+)` : '\\S+');
        continue;
      }

      const grupoId = c.grupoUnion;
      const positions = grupoPos.get(grupoId) ?? [];
      const leaderCampo = campos.find(x => x.pos === positions[0])!;
      const hasName = leaderCampo.campoBd.trim() !== '';

      if (this.sonContiguas(positions)) {
        const isFirst = c.pos === positions[0];
        const isLast  = c.pos === positions[positions.length - 1];
        if (isFirst) {
          partes.push(hasName ? `(?P<${leaderCampo.nombre}>\\S+` : '(?:\\S+');
        } else {
          partes[partes.length - 1] += '\\s+\\S+';
        }
        if (isLast) partes[partes.length - 1] += ')';
      } else {
        const fragIdx = grupoFragIdx.get(grupoId) ?? 0;
        grupoFragIdx.set(grupoId, fragIdx + 1);
        const fragName = `${leaderCampo.nombre}_f${fragIdx}`;
        partes.push(hasName ? `(?P<${fragName}>\\S+)` : '\\S+');
      }
    }

    return `^${partes.join('\\s+')}`;
  }

  private calcCampos(campos: CampoWizard[], excluidas = new Set<number>()) {
    const resultado: any[] = [];
    let orden = 0;

    // Mapa grupoId → posiciones activas ordenadas
    const grupoPos = new Map<number, number[]>();
    for (const c of campos) {
      if (c.grupoUnion !== null && !excluidas.has(c.pos + 1)) {
        if (!grupoPos.has(c.grupoUnion)) grupoPos.set(c.grupoUnion, []);
        grupoPos.get(c.grupoUnion)!.push(c.pos);
      }
    }
    for (const [id, pos] of grupoPos) grupoPos.set(id, pos.sort((a, b) => a - b));

    const processedGrupos = new Set<number>();

    for (const c of campos) {
      if (excluidas.has(c.pos + 1)) continue;

      if (c.grupoUnion !== null) {
        const grupoId = c.grupoUnion;
        if (processedGrupos.has(grupoId)) continue;
        processedGrupos.add(grupoId);

        const positions = grupoPos.get(grupoId) ?? [];
        const leaderCampo = campos.find(x => x.pos === positions[0])!;
        if (!leaderCampo?.campoBd.trim()) continue;

        if (this.sonContiguas(positions)) {
          resultado.push({
            nombre_grupo: leaderCampo.nombre,
            campo_bd: leaderCampo.campoBd.trim(),
            tipo_dato: leaderCampo.tipo,
            longitud: leaderCampo.tipo === 'varchar' ? (leaderCampo.longitud ?? 255) : null,
            opcional: false, valor_defecto: null, orden: orden++,
          });
        } else {
          const fragmentNames = positions.map((_, fi) => `${leaderCampo.nombre}_f${fi}`);
          resultado.push({
            nombre_grupo: fragmentNames[0],
            nombres_grupos_union: fragmentNames.join(','),
            campo_bd: leaderCampo.campoBd.trim(),
            tipo_dato: leaderCampo.tipo,
            longitud: leaderCampo.tipo === 'varchar' ? (leaderCampo.longitud ?? 255) : null,
            opcional: false, valor_defecto: null, orden: orden++,
          });
        }
      } else {
        if (!c.campoBd.trim()) continue;
        resultado.push({
          nombre_grupo: c.nombre.trim(),
          campo_bd: c.campoBd.trim(),
          tipo_dato: c.tipo,
          longitud: c.tipo === 'varchar' ? (c.longitud ?? 255) : null,
          opcional: false, valor_defecto: null, orden: orden++,
        });
      }
    }
    return resultado;
  }

  // ── Guardar ──────────────────────────────────────────────────────────────
  guardar(): void {
    if (!this.puedeGuardar()) return;
    const payload: any = {
      ...this.form.value,
      tabla_destino: this.tablaEfectiva(),
      descripcion: this.form.value.descripcion || null,
      separador_campos: this.delimitador() || ' ',
      filtro_where: this.filtroWhere().trim() || null,
      patrones: this.regexGenerado()
        ? [{ expresion_regular: this.regexGenerado(), orden: 0, activo: true }]
        : [],
      campos: this.camposGenerados(),
      fuentes: this.rutaDirectorio()
        ? [{ ruta_patron: this.rutaDirectorio(), descripcion: null, activo: true }]
        : [],
    };
    this.guardando.set(true);
    this.errorGuardar.set(null);
    this.parsersService.crear(payload).subscribe({
      next: () => this.router.navigate(['/parsers']),
      error: (e) => {
        this.errorGuardar.set(e.error?.detail ?? 'Error al guardar el parser.');
        this.guardando.set(false);
      },
    });
  }

  // ── Drag & drop de columnas ───────────────────────────────────────────────
  onColDragStart(n: number, event: DragEvent): void {
    // Si el usuario arrastra antes de seleccionar línea plantilla, el order está vacío.
    // Lo inicializamos aquí con el orden secuencial actual.
    if (this.columnDisplayOrder().length === 0) {
      const nMax = this.maxTokens();
      if (nMax > 0) this.columnDisplayOrder.set(Array.from({ length: nMax }, (_, i) => i + 1));
    }
    this._dragSourceN = n;
    this.dragSourceCol.set(n);
    this.draggingActive.set(true);
    event.dataTransfer!.effectAllowed = 'move';
    event.dataTransfer!.setData('text/plain', String(n));
  }

  onColDragOver(n: number, event: DragEvent): void {
    event.preventDefault();
    event.dataTransfer!.dropEffect = 'move';
    if (this.dragOverCol() !== n) this.dragOverCol.set(n);
  }

  onColDrop(targetN: number, event: DragEvent): void {
    event.preventDefault();
    const sourceN = this._dragSourceN;
    this._dragSourceN = null;
    this.dragSourceCol.set(null);
    this.dragOverCol.set(null);
    if (sourceN === null || sourceN === targetN) return;

    const cs = this.campos();

    // Todos los n del grupo origen (o solo sourceN si es columna suelta)
    const sourceGrupoId = cs.find(c => c.pos === sourceN - 1)?.grupoUnion ?? null;
    const sourceNs: number[] = sourceGrupoId !== null
      ? this.columnDisplayOrder().filter(n => cs.find(c => c.pos === n - 1)?.grupoUnion === sourceGrupoId)
      : [sourceN];

    // Primer n del grupo destino (o targetN si es columna suelta)
    const targetGrupoId = cs.find(c => c.pos === targetN - 1)?.grupoUnion ?? null;
    const targetFirstN: number = targetGrupoId !== null
      ? (this.columnDisplayOrder().find(n => cs.find(c => c.pos === n - 1)?.grupoUnion === targetGrupoId) ?? targetN)
      : targetN;

    this.columnDisplayOrder.update(order => {
      const withoutSource = order.filter(n => !sourceNs.includes(n));
      const toIdx = withoutSource.indexOf(targetFirstN);
      if (toIdx === -1) return order;
      withoutSource.splice(toIdx, 0, ...sourceNs);
      return withoutSource;
    });
  }

  onColDragEnd(): void {
    this._dragSourceN = null;
    this.dragSourceCol.set(null);
    this.dragOverCol.set(null);
    this.draggingActive.set(false);
  }

  // Devuelve el pos del líder de un grupo (mínimo pos → coherente con calcRegex/calcCampos)
  liderPosDe(positions: number[]): number {
    return Math.min(...positions);
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  mostrarFormato(tipo: TipoDato): boolean {
    return tipo === 'date' || tipo === 'datetime';
  }

  formatoPlaceholder(tipo: TipoDato): string {
    return tipo === 'date' ? 'dd/MM/yyyy' : 'dd/MM/yyyy HH:mm:ss';
  }

  onFiltroChange(valor: string): void {
    this.filtroWhere.set(valor);
    const error = QlikFilter.validate(valor);
    this.filtroError.set(error);
  }

  // Concatena los tokens de varias posiciones (para mostrar un grupo como una sola celda)
  getTokensConcatenados(positions: number[], tokens: string[]): string {
    return positions.map(p => tokens[p] ?? '').filter(t => t.trim()).join(' ');
  }

  esFicheroSeleccionado(ruta: string): boolean {
    return this.exploradorSeleccionado() === ruta;
  }

  esLineaSeleccionada(linea: LineaPreview): boolean {
    return this.lineaSeleccionada()?.numero === linea.numero;
  }
}
