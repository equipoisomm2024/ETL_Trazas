import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { TareaScheduler, TareaSchedulerActualizar, TareaSchedulerCrear } from '../models';

@Injectable({ providedIn: 'root' })
export class TareasService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/tareas';

  listar(): Observable<TareaScheduler[]> {
    return this.http.get<TareaScheduler[]>(`${this.base}/`);
  }

  obtener(id: number): Observable<TareaScheduler> {
    return this.http.get<TareaScheduler>(`${this.base}/${id}`);
  }

  crear(payload: TareaSchedulerCrear): Observable<TareaScheduler> {
    return this.http.post<TareaScheduler>(`${this.base}/`, payload);
  }

  actualizar(id: number, cambios: TareaSchedulerActualizar): Observable<TareaScheduler> {
    return this.http.patch<TareaScheduler>(`${this.base}/${id}`, cambios);
  }

  eliminar(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  activar(id: number): Observable<TareaScheduler> {
    return this.http.post<TareaScheduler>(`${this.base}/${id}/activar`, {});
  }

  desactivar(id: number): Observable<TareaScheduler> {
    return this.http.post<TareaScheduler>(`${this.base}/${id}/desactivar`, {});
  }

  ejecutarAhora(id: number): Observable<{ mensaje: string }> {
    return this.http.post<{ mensaje: string }>(`${this.base}/${id}/ejecutar-ahora`, {});
  }
}
