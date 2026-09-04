import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('inicia como não autenticado sem token', () => {
    expect(service.estaAutenticado()).toBeFalse();
  });

  it('armazena o token e marca autenticado no login com sucesso', () => {
    let concluido = false;
    service.login({ username: 'sindico', password: 'senha' }).subscribe(() => (concluido = true));

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/api/v1/auth/login`);
    expect(req.request.method).toBe('POST');
    req.flush({ access_token: 'abc.def.ghi', token_type: 'bearer' });

    expect(concluido).toBeTrue();
    expect(service.getToken()).toBe('abc.def.ghi');
    expect(service.estaAutenticado()).toBeTrue();
  });

  it('mapeia 401 para mensagem de credenciais inválidas', () => {
    let erro: Error | undefined;
    service.login({ username: 'x', password: 'y' }).subscribe({ error: (e) => (erro = e) });

    httpMock.expectOne(`${environment.apiBaseUrl}/api/v1/auth/login`).flush(
      { detail: 'Credenciais inválidas' },
      { status: 401, statusText: 'Unauthorized' }
    );

    expect(erro?.message).toContain('Credenciais inválidas');
    expect(service.estaAutenticado()).toBeFalse();
  });

  it('logout limpa o token e o estado', () => {
    localStorage.setItem('condoguard_token', 'abc.def.ghi');
    service.logout();
    expect(service.getToken()).toBeNull();
    expect(service.estaAutenticado()).toBeFalse();
  });
});
