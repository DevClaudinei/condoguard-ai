import { Injectable, inject } from '@angular/core';
import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AuthService } from '../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private readonly auth = inject(AuthService);

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const token = this.auth.getToken();

    // Anexa o Bearer apenas em chamadas à própria API (não vaza token a terceiros).
    if (token && req.url.startsWith(environment.apiBaseUrl)) {
      req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
    }

    return next.handle(req).pipe(
      catchError((erro: HttpErrorResponse) => {
        // Token expirado/revogado: encerra a sessão para devolver o usuário ao login.
        if (erro.status === 401) {
          this.auth.logout();
        }
        return throwError(() => erro);
      })
    );
  }
}
