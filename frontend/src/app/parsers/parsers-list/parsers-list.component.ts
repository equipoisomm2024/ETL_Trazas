import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ParsersService } from '../../core/api/parsers.service';
import { ConfiguracionParserResumen } from '../../core/models';

@Component({
  selector: 'app-parsers-list',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './parsers-list.component.html',
})
export class ParsersListComponent implements OnInit {
  private readonly svc = inject(ParsersService);

  parsers = signal<ConfiguracionParserResumen[]>([]);
  cargando = signal(false);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.svc.listar().subscribe({
      next: (data) => { this.parsers.set(data); this.cargando.set(false); },
      error: (e) => { this.error.set('Error al cargar los parsers.'); this.cargando.set(false); },
    });
  }

  toggleActivo(parser: ConfiguracionParserResumen): void {
    this.svc.actualizar(parser.id, { activo: !parser.activo }).subscribe({
      next: () => this.cargar(),
      error: () => this.error.set('Error al actualizar el parser.'),
    });
  }

  eliminar(parser: ConfiguracionParserResumen): void {
    if (!confirm(`¿Eliminar el parser "${parser.nombre}"? Esta acción no se puede deshacer.`)) return;
    this.svc.eliminar(parser.id).subscribe({
      next: () => this.cargar(),
      error: () => this.error.set('Error al eliminar el parser.'),
    });
  }
}
