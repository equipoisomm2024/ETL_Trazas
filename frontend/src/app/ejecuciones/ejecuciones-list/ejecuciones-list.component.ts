import { Component, inject, OnInit, signal } from '@angular/core';
import { NgClass } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EjecucionesService } from '../../core/api/ejecuciones.service';
import { ControlCarga, ListaEjecuciones } from '../../core/models';

@Component({
  selector: 'app-ejecuciones-list',
  standalone: true,
  imports: [RouterLink, FormsModule, NgClass],
  templateUrl: './ejecuciones-list.component.html',
})
export class EjecucionesListComponent implements OnInit {
  private readonly svc = inject(EjecucionesService);

  lista = signal<ListaEjecuciones>({ total: 0, limit: 25, offset: 0, items: [] });
  cargando = signal(false);
  error = signal<string | null>(null);
  detalle = signal<ControlCarga | null>(null);

  filtroEstado = '';
  filtroFichero = '';
  readonly limit = 25;

  ngOnInit(): void { this.cargar(0); }

  cargar(offset: number): void {
    this.cargando.set(true);
    this.error.set(null);
    this.svc.listar({
      estado: this.filtroEstado || undefined,
      fichero: this.filtroFichero || undefined,
      limit: this.limit,
      offset,
    }).subscribe({
      next: (data) => { this.lista.set(data); this.cargando.set(false); },
      error: () => { this.error.set('Error al cargar las ejecuciones.'); this.cargando.set(false); },
    });
  }

  aplicarFiltros(): void { this.cargar(0); }

  get paginaActual(): number { return Math.floor(this.lista().offset / this.limit) + 1; }
  get totalPaginas(): number { return Math.ceil(this.lista().total / this.limit); }

  anterior(): void {
    if (this.lista().offset > 0) this.cargar(this.lista().offset - this.limit);
  }
  siguiente(): void {
    if (this.lista().offset + this.limit < this.lista().total)
      this.cargar(this.lista().offset + this.limit);
  }

  verDetalle(ejec: ControlCarga): void {
    this.detalle.set(ejec);
  }

  cerrarDetalle(): void { this.detalle.set(null); }

  formatFecha(iso: string | null): string {
    if (!iso) return '—';
    return iso.slice(0, 19).replace('T', ' ');
  }

  estadoClase(estado: string): string {
    return { COMPLETADO: 'badge-ok', EN_PROCESO: 'badge-info', ERROR: 'badge-error' }[estado] ?? '';
  }
}
