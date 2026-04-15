import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ParsersService } from '../../core/api/parsers.service';
import { TIPOS_DATO } from '../../core/models';

@Component({
  selector: 'app-parser-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './parser-form.component.html',
})
export class ParserFormComponent implements OnInit {
  private readonly svc = inject(ParsersService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly tiposDato = TIPOS_DATO;
  readonly tabActiva = signal<'datos' | 'patrones' | 'campos' | 'fuentes'>('datos');

  idParser = signal<number | null>(null);
  esEdicion = signal(false);
  guardando = signal(false);
  error = signal<string | null>(null);

  form: FormGroup = this.fb.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    descripcion: [''],
    tabla_destino: ['', Validators.required],
    activo: [true],
    patrones: this.fb.array([]),
    campos: this.fb.array([]),
    fuentes: this.fb.array([]),
  });

  get patrones(): FormArray { return this.form.get('patrones') as FormArray; }
  get campos(): FormArray { return this.form.get('campos') as FormArray; }
  get fuentes(): FormArray { return this.form.get('fuentes') as FormArray; }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.idParser.set(+id);
      this.esEdicion.set(true);
      this.cargarParser(+id);
    }
  }

  private cargarParser(id: number): void {
    this.svc.obtener(id).subscribe({
      next: (p) => {
        this.form.patchValue({
          nombre: p.nombre,
          descripcion: p.descripcion ?? '',
          tabla_destino: p.tabla_destino,
          activo: p.activo,
        });
        p.patrones.forEach((pat) => this.patrones.push(this.nuevoPatronGroup(pat)));
        p.campos.forEach((c) => this.campos.push(this.nuevoCampoGroup(c)));
        p.fuentes.forEach((f) => this.fuentes.push(this.nuevaFuenteGroup(f)));
      },
      error: () => this.error.set('Error al cargar el parser.'),
    });
  }

  // --- Patrones ---
  nuevoPatronGroup(datos?: any): FormGroup {
    return this.fb.group({
      expresion_regular: [datos?.expresion_regular ?? '', Validators.required],
      orden: [datos?.orden ?? 0],
      activo: [datos?.activo ?? true],
    });
  }
  agregarPatron(): void { this.patrones.push(this.nuevoPatronGroup()); }
  quitarPatron(i: number): void { this.patrones.removeAt(i); }

  // --- Campos ---
  nuevoCampoGroup(datos?: any): FormGroup {
    return this.fb.group({
      nombre_grupo: [datos?.nombre_grupo ?? '', Validators.required],
      campo_bd: [datos?.campo_bd ?? '', Validators.required],
      tipo_dato: [datos?.tipo_dato ?? 'text', Validators.required],
      longitud: [datos?.longitud ?? null],
      opcional: [datos?.opcional ?? false],
      valor_defecto: [datos?.valor_defecto ?? ''],
      orden: [datos?.orden ?? 0],
    });
  }
  agregarCampo(): void { this.campos.push(this.nuevoCampoGroup()); }
  quitarCampo(i: number): void { this.campos.removeAt(i); }

  // --- Fuentes ---
  nuevaFuenteGroup(datos?: any): FormGroup {
    return this.fb.group({
      ruta_patron: [datos?.ruta_patron ?? '', Validators.required],
      descripcion: [datos?.descripcion ?? ''],
      activo: [datos?.activo ?? true],
    });
  }
  agregarFuente(): void { this.fuentes.push(this.nuevaFuenteGroup()); }
  quitarFuente(i: number): void { this.fuentes.removeAt(i); }

  // --- Submit ---
  guardar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.tabActiva.set('datos');
      return;
    }

    const payload = {
      ...this.form.value,
      descripcion: this.form.value.descripcion || null,
      campos: this.form.value.campos.map((c: any) => ({
        ...c,
        longitud: c.longitud || null,
        valor_defecto: c.valor_defecto || null,
      })),
      fuentes: this.form.value.fuentes.map((f: any) => ({
        ...f,
        descripcion: f.descripcion || null,
      })),
    };

    this.guardando.set(true);
    this.error.set(null);

    const op$ = this.esEdicion()
      ? this.svc.reemplazar(this.idParser()!, payload)
      : this.svc.crear(payload);

    op$.subscribe({
      next: () => this.router.navigate(['/parsers']),
      error: (e) => {
        this.error.set(e.error?.detail ?? 'Error al guardar el parser.');
        this.guardando.set(false);
      },
    });
  }

  campoInvalido(grupo: FormGroup, campo: string): boolean {
    const ctrl = grupo.get(campo);
    return !!(ctrl?.invalid && ctrl?.touched);
  }
}
