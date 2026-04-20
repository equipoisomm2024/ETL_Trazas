import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ControlCarga,
  ListaEjecuciones,
  ProcesarRequest,
  ProcesarResponse,
} from '../models';

@Injectable({ providedIn: 'root' })
export class EjecucionesService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/ejecuciones';

  listar(params: {
    estado?: string;
    fichero?: string;
    limit?: number;
    offset?: number;
  } = {}): Observable<ListaEjecuciones> {
    let p = new HttpParams();
    if (params.estado) p = p.set('estado', params.estado);
    if (params.fichero) p = p.set('fichero', params.fichero);
    if (params.limit !== undefined) p = p.set('limit', params.limit);
    if (params.offset !== undefined) p = p.set('offset', params.offset);
    return this.http.get<ListaEjecuciones>(`${this.base}/`, { params: p });
  }

  obtener(idEjecucion: string): Observable<ControlCarga> {
    return this.http.get<ControlCarga>(`${this.base}/${idEjecucion}`);
  }

  procesar(payload: ProcesarRequest): Observable<ProcesarResponse> {
    return this.http.post<ProcesarResponse>(`${this.base}/procesar`, payload);
  }
}
