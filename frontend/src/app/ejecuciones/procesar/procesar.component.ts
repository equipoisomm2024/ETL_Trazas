import { Component, inject, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EjecucionesService } from '../../core/api/ejecuciones.service';
import { ParsersService } from '../../core/api/parsers.service';
import { ConfiguracionParserResumen, ProcesarResponse } from '../../core/models';

type FuenteTipo = 'fichero' | 'directorio' | 'fuentes_bd';

@Component({
  selector: 'app-procesar',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './procesar.component.html',
})
export class ProcesarComponent implements OnInit {
  private readonly svc = inject(EjecucionesService);
  private readonly parsersSvc = inject(ParsersService);
  private readonly fb = inject(FormBuilder);

  fuenteTipo = signal<FuenteTipo>('directorio');
  procesando = signal(false);
  error = signal<string | null>(null);
  resultado = signal<ProcesarResponse | null>(null);

  parsers = signal<ConfiguracionParserResumen[]>([]);

  form = this.fb.group({
    ruta: [''],
    id_parser: [null as number | null],
    forzar_completo: [false],
  });

  ngOnInit(): void {
    this.parsersSvc.listar(true).subscribe({
      next: (data) => this.parsers.set(data),
    });
  }

  seleccionarFuente(tipo: FuenteTipo): void {
    this.fuenteTipo.set(tipo);
    this.resultado.set(null);
    this.error.set(null);
    if (tipo === 'fuentes_bd') {
      this.form.get('ruta')?.clearValidators();
    } else {
      this.form.get('ruta')?.setValidators(Validators.required);
    }
    this.form.get('ruta')?.updateValueAndValidity();
  }

  lanzar(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }

    const forzar = this.form.value.forzar_completo ?? false;
    const ruta = this.form.value.ruta ?? '';
    const idParser = this.form.value.id_parser ?? null;

    const base: any = { forzar_completo: forzar };
    if (idParser) base.id_parser = +idParser;

    const payload =
      this.fuenteTipo() === 'fichero'    ? { ...base, fichero: ruta } :
      this.fuenteTipo() === 'directorio' ? { ...base, directorio: ruta } :
                                           { ...base, usar_fuentes_bd: true };

    this.procesando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.svc.procesar(payload).subscribe({
      next: (res) => { this.resultado.set(res); this.procesando.set(false); },
      error: (e) => {
        this.error.set(e.error?.detail ?? 'Error al lanzar el procesamiento.');
        this.procesando.set(false);
      },
    });
  }
}
