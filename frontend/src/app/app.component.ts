import { Component, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Observable } from 'rxjs';
import { AuthService } from './services/auth.service';

const TITULO_BASE = 'CondoGuard AI — Gestão Condominial';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  private readonly authService = inject(AuthService);
  private readonly title = inject(Title);

  abaAtiva: 'morador' | 'sindico' = 'sindico';
  readonly autenticado$: Observable<boolean> = this.authService.autenticado$;

  constructor() {
    this.title.setTitle(TITULO_BASE);
  }

  /** Troca a aba ativa e reflete o contexto no título da aba do navegador. */
  selecionarAba(aba: 'morador' | 'sindico'): void {
    this.abaAtiva = aba;
    const contexto = aba === 'sindico' ? 'Painel do Síndico' : 'Área do Morador';
    this.title.setTitle(`${contexto} · ${TITULO_BASE}`);
  }
}
