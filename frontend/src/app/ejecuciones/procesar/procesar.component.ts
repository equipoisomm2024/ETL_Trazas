import { Component, inject, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EjecucionesService } from '../../core/api/ejecuciones.service';
import { ParsersService } from '../../core/api/parsers.service';
import { FilesService, ContenidoDirectorio, EntradaDirectorio } from '../../core/api/files.service';
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
  private readonly filesSvc = inject(FilesService);
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

  // ── Explorador ────────────────────────────────────────────────────────────
  mostrarExplorador = signal(false);
  explorador = signal<ContenidoDirectorio | null>(null);
  exploradorCargando = signal(false);
  exploradorError = signal<string | null>(null);
  exploradorSeleccionado = signal<string | null>(null);
  exploradorRutaManual = signal('');
  private _ultimoDirectorio = '/workspace/proyectos/ETL_Trazas/Pruebas';

  ngOnInit(): void {
    this.parsersSvc.listar(true).subscribe({
      next: (data) => this.parsers.set(data),
    });
  }

  seleccionarFuente(tipo: FuenteTipo): void {
    this.fuenteTipo.set(tipo);
    this.resultado.set(null);
    this.error.set(null);
    this.form.patchValue({ ruta: '' });
    if (tipo === 'fuentes_bd') {
      this.form.get('ruta')?.clearValidators();
    } else {
      this.form.get('ruta')?.setValidators(Validators.required);
    }
    this.form.get('ruta')?.updateValueAndValidity();
  }

  // ── Explorador: abrir, navegar, seleccionar ───────────────────────────────
  abrirExplorador(): void {
    this.mostrarExplorador.set(true);
    this.exploradorSeleccionado.set(null);
    this.navegarExplorador(this._ultimoDirectorio);
  }

  navegarExplorador(path: string): void {
    if (!path.trim()) return;
    this.exploradorCargando.set(true);
    this.exploradorError.set(null);
    this.exploradorSeleccionado.set(null);
    this.filesSvc.browse(path).subscribe({
      next: (data) => {
        this.explorador.set(data);
        this.exploradorRutaManual.set(data.ruta_actual);
        this._ultimoDirectorio = data.ruta_actual;
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
      if (this.fuenteTipo() === 'directorio') {
        // En modo directorio, marcar el directorio como seleccionado (sin navegar)
        // Un clic selecciona, doble clic navega dentro
        this.exploradorSeleccionado.set(
          this.exploradorSeleccionado() === entrada.ruta ? null : entrada.ruta
        );
      } else {
        // En modo fichero, navegar dentro del directorio
        this.navegarExplorador(entrada.ruta);
      }
    } else {
      if (this.fuenteTipo() === 'fichero') {
        this.exploradorSeleccionado.set(
          this.exploradorSeleccionado() === entrada.ruta ? null : entrada.ruta
        );
      }
      // En modo directorio, los ficheros no son seleccionables
    }
  }

  entradaEsSeleccionable(entrada: EntradaDirectorio): boolean {
    if (this.fuenteTipo() === 'directorio') return entrada.es_directorio;
    return !entrada.es_directorio;
  }

  confirmarSeleccion(): void {
    const sel = this.exploradorSeleccionado();
    if (!sel) return;
    this.form.patchValue({ ruta: sel });
    this._ultimoDirectorio = this.explorador()?.ruta_actual ?? this._ultimoDirectorio;
    this.mostrarExplorador.set(false);
  }

  confirmarDirectorioActual(): void {
    const ruta = this.explorador()?.ruta_actual;
    if (!ruta) return;
    this.form.patchValue({ ruta });
    this._ultimoDirectorio = ruta;
    this.mostrarExplorador.set(false);
  }

  onRutaManualKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') this.navegarExplorador(this.exploradorRutaManual());
  }

  esFicheroSeleccionado(ruta: string): boolean {
    return this.exploradorSeleccionado() === ruta;
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
