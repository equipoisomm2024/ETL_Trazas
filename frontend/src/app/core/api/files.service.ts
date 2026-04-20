import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface EntradaDirectorio {
  nombre: string;
  ruta: string;
  es_directorio: boolean;
  extension: string | null;
}

export interface ContenidoDirectorio {
  ruta_actual: string;
  ruta_padre: string | null;
  entradas: EntradaDirectorio[];
}

export interface PreviewRequest {
  ruta: string;
  delimitador: string;
  num_lineas: number;
}

export interface CampoDetectado {
  posicion: number;
  valor: string;
}

export interface LineaPreview {
  numero: number;
  contenido: string;
  campos: CampoDetectado[];
}

export interface PreviewResponse {
  ruta: string;
  delimitador: string;
  lineas: LineaPreview[];
  num_campos: number;
}

@Injectable({ providedIn: 'root' })
export class FilesService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/files';

  browse(path: string): Observable<ContenidoDirectorio> {
    return this.http.get<ContenidoDirectorio>(`${this.base}/browse`, {
      params: new HttpParams().set('path', path),
    });
  }

  preview(req: PreviewRequest): Observable<PreviewResponse> {
    return this.http.post<PreviewResponse>(`${this.base}/preview`, req);
  }
}
