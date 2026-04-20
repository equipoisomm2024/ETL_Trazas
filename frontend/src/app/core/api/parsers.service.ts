import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ConfiguracionParser,
  ConfiguracionParserCrear,
  ConfiguracionParserResumen,
  CampoExtraccion,
  PatronExtraccion,
  FuenteFichero,
} from '../models';

@Injectable({ providedIn: 'root' })
export class ParsersService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/parsers';

  listar(soloActivos = false): Observable<ConfiguracionParserResumen[]> {
    const params = soloActivos ? new HttpParams().set('solo_activos', 'true') : undefined;
    return this.http.get<ConfiguracionParserResumen[]>(`${this.base}/`, { params });
  }

  obtener(id: number): Observable<ConfiguracionParser> {
    return this.http.get<ConfiguracionParser>(`${this.base}/${id}`);
  }

  crear(payload: ConfiguracionParserCrear): Observable<ConfiguracionParser> {
    return this.http.post<ConfiguracionParser>(`${this.base}/`, payload);
  }

  reemplazar(id: number, payload: ConfiguracionParserCrear): Observable<ConfiguracionParser> {
    return this.http.put<ConfiguracionParser>(`${this.base}/${id}`, payload);
  }

  actualizar(id: number, cambios: Partial<ConfiguracionParser>): Observable<ConfiguracionParser> {
    return this.http.patch<ConfiguracionParser>(`${this.base}/${id}`, cambios);
  }

  eliminar(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  // Patrones
  agregarPatron(idParser: number, patron: Omit<PatronExtraccion, 'id' | 'id_parser'>): Observable<PatronExtraccion> {
    return this.http.post<PatronExtraccion>(`${this.base}/${idParser}/patrones`, patron);
  }

  actualizarPatron(idParser: number, idPatron: number, cambios: Partial<PatronExtraccion>): Observable<PatronExtraccion> {
    return this.http.patch<PatronExtraccion>(`${this.base}/${idParser}/patrones/${idPatron}`, cambios);
  }

  eliminarPatron(idParser: number, idPatron: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${idParser}/patrones/${idPatron}`);
  }

  // Campos
  agregarCampo(idParser: number, campo: Omit<CampoExtraccion, 'id' | 'id_parser'>): Observable<CampoExtraccion> {
    return this.http.post<CampoExtraccion>(`${this.base}/${idParser}/campos`, campo);
  }

  actualizarCampo(idParser: number, idCampo: number, cambios: Partial<CampoExtraccion>): Observable<CampoExtraccion> {
    return this.http.patch<CampoExtraccion>(`${this.base}/${idParser}/campos/${idCampo}`, cambios);
  }

  eliminarCampo(idParser: number, idCampo: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${idParser}/campos/${idCampo}`);
  }

  // Fuentes
  agregarFuente(idParser: number, fuente: Omit<FuenteFichero, 'id' | 'id_parser'>): Observable<FuenteFichero> {
    return this.http.post<FuenteFichero>(`${this.base}/${idParser}/fuentes`, fuente);
  }

  actualizarFuente(idParser: number, idFuente: number, cambios: Partial<FuenteFichero>): Observable<FuenteFichero> {
    return this.http.patch<FuenteFichero>(`${this.base}/${idParser}/fuentes/${idFuente}`, cambios);
  }

  eliminarFuente(idParser: number, idFuente: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${idParser}/fuentes/${idFuente}`);
  }
}
