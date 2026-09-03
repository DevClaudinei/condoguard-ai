import { TestBed } from '@angular/core/testing';
import { CommonModule } from '@angular/common';
import { AppComponent } from './app.component';
import { NovoChamadoComponent } from './components/novo-chamado/novo-chamado.component';
import { PainelSindicoComponent } from './components/painel-sindico/painel-sindico.component';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';

describe('AppComponent', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [CommonModule, HttpClientTestingModule, ReactiveFormsModule],
    declarations: [AppComponent, NovoChamadoComponent, PainelSindicoComponent]
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('deve iniciar na aba do síndico por padrão', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.abaAtiva).toEqual('sindico');
  });

  it('deve renderizar a marca no cabeçalho', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.brand')?.textContent).toContain('CondoGuard AI');
  });
});
