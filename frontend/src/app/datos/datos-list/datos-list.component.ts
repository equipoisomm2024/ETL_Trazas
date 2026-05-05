import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { DatosService, TablaInfo, DatosPaginados } from '../../core/api/datos.service';

@Component({
  selector: 'app-datos-list',
  standalone: true,
  imports: [],
  templateUrl: './datos-list.component.html',
})
export class DatosListComponent implements OnInit {
  private readonly svc = inject(DatosService);

  tablas = signal<TablaInfo[]>([]);
  tablaSeleccionada = signal<string | null>(null);
  datos = signal<DatosPaginados | null>(null);
  cargandoTablas = signal(true);
  cargandoDatos = signal(false);
  error = signal<string | null>(null);
  page = signal(1);
  limit = signal(25);

  paginasMostrar = computed(() => {
    const d = this.datos();
    if (!d) return [];
    const total = d.pages;
    const cur = d.page;
    const pages: (number | '...')[] = [];
    for (let i = 1; i <= total; i++) {
      if (i === 1 || i === total || (i >= cur - 2 && i <= cur + 2)) {
        pages.push(i);
      } else if (pages[pages.length - 1] !== '...') {
        pages.push('...');
      }
    }
    return pages;
  });

  ngOnInit(): void {
    this.svc.listarTablas().subscribe({
      next: (tablas) => {
        this.tablas.set(tablas);
        this.cargandoTablas.set(false);
        // Auto-seleccionar la primera tabla con registros
        const primera = tablas.find(t => (t.registros ?? 0) > 0);
        if (primera) this.seleccionarTabla(primera.tabla);
      },
      error: () => this.cargandoTablas.set(false),
    });
  }

  seleccionarTabla(tabla: string): void {
    if (this.tablaSeleccionada() === tabla && this.datos()) return;
    this.tablaSeleccionada.set(tabla);
    this.page.set(1);
    this.cargarDatos();
  }

  irPagina(p: number | '...'): void {
    if (p === '...') return;
    this.page.set(p);
    this.cargarDatos();
  }

  cambiarLimit(event: Event): void {
    this.limit.set(+((event.target as HTMLSelectElement).value));
    this.page.set(1);
    this.cargarDatos();
  }

  recargar(): void {
    this.cargarDatos();
  }

  private cargarDatos(): void {
    const tabla = this.tablaSeleccionada();
    if (!tabla) return;
    this.cargandoDatos.set(true);
    this.error.set(null);
    this.svc.obtenerDatos(tabla, this.page(), this.limit()).subscribe({
      next: (d) => { this.datos.set(d); this.cargandoDatos.set(false); },
      error: (e) => {
        this.error.set(e.error?.detail ?? 'Error al cargar los datos.');
        this.cargandoDatos.set(false);
      },
    });
  }

  formatearValor(val: any): string {
    if (val === null || val === undefined) return '—';
    if (typeof val === 'boolean') return val ? 'Sí' : 'No';
    return String(val);
  }

  esNumero(val: any): boolean {
    return typeof val === 'number';
  }
}
