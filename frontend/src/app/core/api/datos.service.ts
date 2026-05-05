import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TablaInfo {
  tabla: string;
  registros: number | null;
}

export interface DatosPaginados {
  tabla: string;
  columnas: string[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  filas: Record<string, any>[];
}

@Injectable({ providedIn: 'root' })
export class DatosService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/datos';

  listarTablas(): Observable<TablaInfo[]> {
    return this.http.get<TablaInfo[]>(`${this.base}/tablas`);
  }

  obtenerDatos(tabla: string, page = 1, limit = 25): Observable<DatosPaginados> {
    const params = new HttpParams().set('page', page).set('limit', limit);
    return this.http.get<DatosPaginados>(`${this.base}/${tabla}`, { params });
  }
}
