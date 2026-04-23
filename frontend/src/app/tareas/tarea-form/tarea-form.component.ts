import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TareasService } from '../../core/api/tareas.service';
import { ParsersService } from '../../core/api/parsers.service';
import { TareaScheduler, TareaSchedulerCrear, ConfiguracionParserResumen, TipoFuente } from '../../core/models';

interface FormData {
  nombre: string;
  descripcion: string;
  cron_expression: string;
  tipo_fuente: TipoFuente;
  ruta: string;
  id_parser: number | null;
  forzar_completo: boolean;
  activo: boolean;
}

const PRESETS_CRON: { etiqueta: string; valor: string }[] = [
  { etiqueta: 'Cada 5 minutos', valor: '*/5 * * * *' },
  { etiqueta: 'Cada 15 minutos', valor: '*/15 * * * *' },
  { etiqueta: 'Cada 30 minutos', valor: '*/30 * * * *' },
  { etiqueta: 'Cada hora', valor: '0 * * * *' },
  { etiqueta: 'Cada 6 horas', valor: '0 */6 * * *' },
  { etiqueta: 'Diariamente a medianoche', valor: '0 0 * * *' },
  { etiqueta: 'Diariamente a las 8:00', valor: '0 8 * * *' },
  { etiqueta: 'Lunes a viernes a las 8:00', valor: '0 8 * * 1-5' },
];

@Component({
  selector: 'app-tarea-form',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './tarea-form.component.html',
})
export class TareaFormComponent implements OnInit {
  private readonly svc = inject(TareasService);
  private readonly parsersSvc = inject(ParsersService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly presets = PRESETS_CRON;
  readonly tiposFuente: { valor: TipoFuente; etiqueta: string }[] = [
    { valor: 'fuentes_bd', etiqueta: 'Fuentes configuradas en BD' },
    { valor: 'directorio', etiqueta: 'Directorio' },
    { valor: 'fichero', etiqueta: 'Fichero concreto' },
  ];

  idTarea = signal<number | null>(null);
  guardando = signal(false);
  error = signal<string | null>(null);
  parsers = signal<ConfiguracionParserResumen[]>([]);

  form: FormData = {
    nombre: '',
    descripcion: '',
    cron_expression: '0 * * * *',
    tipo_fuente: 'fuentes_bd',
    ruta: '',
    id_parser: null,
    forzar_completo: false,
    activo: true,
  };

  get esNueva(): boolean {
    return this.idTarea() === null;
  }

  ngOnInit(): void {
    this.parsersSvc.listar(true).subscribe({
      next: (ps) => this.parsers.set(ps),
    });

    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      const numId = parseInt(id, 10);
      this.idTarea.set(numId);
      this.svc.obtener(numId).subscribe({
        next: (t) => this.cargarEnForm(t),
        error: () => this.error.set('No se pudo cargar la tarea.'),
      });
    }
  }

  private cargarEnForm(t: TareaScheduler): void {
    this.form = {
      nombre: t.nombre,
      descripcion: t.descripcion ?? '',
      cron_expression: t.cron_expression,
      tipo_fuente: t.tipo_fuente as TipoFuente,
      ruta: t.ruta ?? '',
      id_parser: t.id_parser,
      forzar_completo: t.forzar_completo,
      activo: t.activo,
    };
  }

  aplicarPreset(valor: string): void {
    this.form.cron_expression = valor;
  }

  guardar(): void {
    this.guardando.set(true);
    this.error.set(null);

    const payload: TareaSchedulerCrear = {
      nombre: this.form.nombre.trim(),
      descripcion: this.form.descripcion.trim() || null,
      cron_expression: this.form.cron_expression.trim(),
      tipo_fuente: this.form.tipo_fuente,
      ruta: this.form.ruta.trim() || null,
      id_parser: this.form.id_parser || null,
      forzar_completo: this.form.forzar_completo,
      activo: this.form.activo,
    };

    const id = this.idTarea();
    const op$ = id
      ? this.svc.actualizar(id, payload)
      : this.svc.crear(payload);

    op$.subscribe({
      next: () => this.router.navigate(['/tareas']),
      error: (e) => {
        const detalle = e?.error?.detail;
        this.error.set(
          typeof detalle === 'string' ? detalle
          : Array.isArray(detalle) ? detalle.map((d: any) => d.msg).join('; ')
          : 'Error al guardar la tarea.'
        );
        this.guardando.set(false);
      },
    });
  }
}
