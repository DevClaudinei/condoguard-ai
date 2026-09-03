import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { ChamadoCreate, ChamadoResponse } from '../models/chamado.model';

@Injectable({
  providedIn: 'root'
})
export class ChamadoService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiBaseUrl}/api/v1/chamados`;

  enviarChamado(payload: ChamadoCreate): Observable<ChamadoResponse> {
    return this.http
      .post<ChamadoResponse>(`${this.apiUrl}/triagem`, payload)
      .pipe(catchError((erro: HttpErrorResponse) => this.tratarErro(erro)));
  }

  listarChamados(): Observable<ChamadoResponse[]> {
    return this.http
      .get<ChamadoResponse[]>(this.apiUrl)
      .pipe(catchError((erro: HttpErrorResponse) => this.tratarErro(erro)));
  }

  private tratarErro(erro: HttpErrorResponse): Observable<never> {
    const detalhe =
      erro.status === 0
        ? 'Falha ao conectar com o servidor de triagem. Verifique se a API FastAPI está ativa.'
        : `A API de triagem respondeu com erro (HTTP ${erro.status}).`;
    return throwError(() => new Error(detalhe));
  }
}
