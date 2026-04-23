import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';
import { TareasService } from '../../core/api/tareas.service';
import { TareaScheduler } from '../../core/models';

@Component({
  selector: 'app-tareas-list',
  standalone: true,
  imports: [RouterLink, DatePipe],
  templateUrl: './tareas-list.component.html',
})
export class TareasListComponent implements OnInit {
  private readonly svc = inject(TareasService);

  tareas = signal<TareaScheduler[]>([]);
  cargando = signal(false);
  error = signal<string | null>(null);
  mensaje = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.svc.listar().subscribe({
      next: (data) => { this.tareas.set(data); this.cargando.set(false); },
      error: () => { this.error.set('Error al cargar las tareas.'); this.cargando.set(false); },
    });
  }

  toggleActivo(tarea: TareaScheduler): void {
    const op$ = tarea.activo ? this.svc.desactivar(tarea.id) : this.svc.activar(tarea.id);
    op$.subscribe({
      next: () => this.cargar(),
      error: () => this.error.set('Error al cambiar el estado de la tarea.'),
    });
  }

  ejecutarAhora(tarea: TareaScheduler): void {
    this.mensaje.set(null);
    this.svc.ejecutarAhora(tarea.id).subscribe({
      next: (res) => {
        this.mensaje.set(res.mensaje);
        setTimeout(() => this.mensaje.set(null), 4000);
      },
      error: () => this.error.set('Error al lanzar la tarea.'),
    });
  }

  eliminar(tarea: TareaScheduler): void {
    if (!confirm(`¿Eliminar la tarea "${tarea.nombre}"? Esta acción no se puede deshacer.`)) return;
    this.svc.eliminar(tarea.id).subscribe({
      next: () => this.cargar(),
      error: () => this.error.set('Error al eliminar la tarea.'),
    });
  }

  etiquetaTipoFuente(tipo: string): string {
    return tipo === 'fuentes_bd' ? 'Fuentes BD'
         : tipo === 'directorio' ? 'Directorio'
         : 'Fichero';
  }
}
