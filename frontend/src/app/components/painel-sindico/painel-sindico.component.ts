import { Component, OnInit } from '@angular/core';
import { ChamadoService } from '../../services/chamado.service';
import { ChamadoResponse, UrgenciaEnum } from '../../models/chamado.model';

@Component({
  selector: 'app-painel-sindico',
  templateUrl: './painel-sindico.component.html',
  styleUrls: ['./painel-sindico.component.scss']
})
export class PainelSindicoComponent implements OnInit {
  chamados: ChamadoResponse[] = [];
  filtroUrgencia: string = 'TODOS';
  carregando = false;

  constructor(private chamadoService: ChamadoService) {}

  ngOnInit(): void {
    this.carregarDados();
  }

  carregarDados(): void {
    this.carregando = true;
    this.chamadoService.listarChamados().subscribe({
      next: (dados) => {
        this.chamados = dados;
        this.carregando = false;
      },
      error: () => {
        this.carregando = false;
      }
    });
  }

  get chamadosFiltrados(): ChamadoResponse[] {
    if (this.filtroUrgencia === 'TODOS') return this.chamados;
    return this.chamados.filter(c => c.urgencia === this.filtroUrgencia);
  }

  contarPorUrgencia(urgencia: UrgenciaEnum): number {
    return this.chamados.filter(c => c.urgencia === urgencia).length;
  }
}
