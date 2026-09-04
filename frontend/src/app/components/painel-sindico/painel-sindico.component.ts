import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { BehaviorSubject, Observable, combineLatest, of } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';
import { ChamadoService } from '../../services/chamado.service';
import { ChamadoResponse, UrgenciaEnum } from '../../models/chamado.model';

type FiltroUrgencia = UrgenciaEnum | 'TODOS';

interface PainelViewModel {
  lista: ChamadoResponse[];
  totalP1: number;
  totalP2: number;
  totalP3: number;
  total: number;
}

@Component({
  selector: 'app-painel-sindico',
  templateUrl: './painel-sindico.component.html',
  styleUrls: ['./painel-sindico.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PainelSindicoComponent {
  private readonly chamadoService = inject(ChamadoService);

  private readonly filtro$ = new BehaviorSubject<FiltroUrgencia>('TODOS');
  private readonly refresh$ = new BehaviorSubject<void>(undefined);

  readonly carregando$ = new BehaviorSubject<boolean>(false);
  readonly erroMsg$ = new BehaviorSubject<string>('');

  /** Filtro corrente, exposto ao template para exibição do rótulo ativo. */
  filtroUrgencia: FiltroUrgencia = 'TODOS';

  // View-model reativo: os dados só são recomputados quando a lista ou o filtro mudam,
  // eliminando o recálculo por ciclo de change detection que os getters causavam.
  readonly vm$: Observable<PainelViewModel> = combineLatest([
    this.refresh$.pipe(switchMap(() => this.buscarChamados())),
    this.filtro$
  ]).pipe(
    map(([chamados, filtro]) => this.montarViewModel(chamados, filtro))
  );

  private buscarChamados(): Observable<ChamadoResponse[]> {
    this.carregando$.next(true);
    this.erroMsg$.next('');
    return this.chamadoService.listarChamados().pipe(
      tap(() => this.carregando$.next(false)),
      catchError((erro: Error) => {
        this.erroMsg$.next(erro.message);
        this.carregando$.next(false);
        return of<ChamadoResponse[]>([]);
      })
    );
  }

  private montarViewModel(chamados: ChamadoResponse[], filtro: FiltroUrgencia): PainelViewModel {
    return {
      lista: filtro === 'TODOS' ? chamados : chamados.filter((c) => c.urgencia === filtro),
      totalP1: chamados.filter((c) => c.urgencia === 'P1_CRITICO').length,
      totalP2: chamados.filter((c) => c.urgencia === 'P2_URGENTE').length,
      totalP3: chamados.filter((c) => c.urgencia === 'P3_ROTINA').length,
      total: chamados.length
    };
  }

  aplicarFiltro(filtro: FiltroUrgencia): void {
    this.filtroUrgencia = filtro;
    this.filtro$.next(filtro);
  }

  carregarDados(): void {
    this.refresh$.next();
  }
}
