import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EjecucionesService } from '../../core/api/ejecuciones.service';
import { ProcesarResponse } from '../../core/models';

type FuenteTipo = 'fichero' | 'directorio' | 'fuentes_bd';

@Component({
  selector: 'app-procesar',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './procesar.component.html',
})
export class ProcesarComponent {
  private readonly svc = inject(EjecucionesService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);

  fuenteTipo = signal<FuenteTipo>('directorio');
  procesando = signal(false);
  error = signal<string | null>(null);
  resultado = signal<ProcesarResponse | null>(null);

  form = this.fb.group({
    ruta: [''],
    forzar_completo: [false],
  });

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

    const payload =
      this.fuenteTipo() === 'fichero'    ? { fichero: ruta, forzar_completo: forzar } :
      this.fuenteTipo() === 'directorio' ? { directorio: ruta, forzar_completo: forzar } :
                                           { usar_fuentes_bd: true, forzar_completo: forzar };

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
