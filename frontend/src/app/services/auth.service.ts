import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { LoginRequest, TokenResponse } from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiBaseUrl}/api/v1/auth`;
  private readonly TOKEN_KEY = 'condoguard_token';

  // Estado reativo de autenticação, inicializado a partir do token persistido.
  private readonly _autenticado$ = new BehaviorSubject<boolean>(this.temTokenValido());
  readonly autenticado$: Observable<boolean> = this._autenticado$.asObservable();

  login(credenciais: LoginRequest): Observable<void> {
    return this.http.post<TokenResponse>(`${this.apiUrl}/login`, credenciais).pipe(
      tap((res) => {
        this.salvarToken(res.access_token);
        this._autenticado$.next(true);
      }),
      map(() => void 0),
      catchError((erro: HttpErrorResponse) => {
        const msg =
          erro.status === 401
            ? 'Credenciais inválidas.'
            : 'Falha ao autenticar. Verifique se a API está ativa.';
        return throwError(() => new Error(msg));
      })
    );
  }

  logout(): void {
    this.removerToken();
    this._autenticado$.next(false);
  }

  estaAutenticado(): boolean {
    return this._autenticado$.value;
  }

  getToken(): string | null {
    try {
      return localStorage.getItem(this.TOKEN_KEY);
    } catch {
      return null;
    }
  }

  private salvarToken(token: string): void {
    try {
      localStorage.setItem(this.TOKEN_KEY, token);
    } catch {
      /* modo privado/sem storage: mantém sessão apenas em memória via BehaviorSubject */
    }
  }

  private removerToken(): void {
    try {
      localStorage.removeItem(this.TOKEN_KEY);
    } catch {
      /* silencioso: nada a limpar se o storage não estiver acessível */
    }
  }

  /** Verifica se há token e se o claim `exp` ainda não expirou. */
  private temTokenValido(): boolean {
    const token = this.getToken();
    if (!token) {
      return false;
    }
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (typeof payload.exp !== 'number') {
        return true; // sem exp: trata como válido até o backend rejeitar
      }
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }
}
