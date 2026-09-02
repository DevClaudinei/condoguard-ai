import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ChamadoCreate, ChamadoResponse } from '../models/chamado.model';

@Injectable({
  providedIn: 'root'
})
export class ChamadoService {
  private readonly apiUrl = 'http://127.0.0.1:8000/api/v1/chamados';

  constructor(private http: HttpClient) {}

  enviarChamado(payload: ChamadoCreate): Observable<ChamadoResponse> {
    return this.http.post<ChamadoResponse>(`${this.apiUrl}/triagem`, payload);
  }

  listarChamados(): Observable<ChamadoResponse[]> {
    return this.http.get<ChamadoResponse[]>(this.apiUrl);
  }
}
