import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ChamadoService } from '../../services/chamado.service';
import { ChamadoResponse } from '../../models/chamado.model';

@Component({
  selector: 'app-novo-chamado',
  templateUrl: './novo-chamado.component.html',
  styleUrls: ['./novo-chamado.component.scss']
})
export class NovoChamadoComponent {
  chamadoForm: FormGroup;
  loading = false;
  resultado: ChamadoResponse | null = null;
  erroMsg = '';

  constructor(
    private fb: FormBuilder,
    private chamadoService: ChamadoService
  ) {
    this.chamadoForm = this.fb.group({
      torre: ['Torre A', [Validators.required]],
      apartamento: ['', [Validators.required, Validators.maxLength(6)]],
      titulo: ['', [Validators.required, Validators.minLength(3)]],
      descricao: ['', [Validators.required, Validators.minLength(5)]]
    });
  }

  submeter() {
    if (this.chamadoForm.invalid) return;

    this.loading = true;
    this.resultado = null;
    this.erroMsg = '';

    this.chamadoService.enviarChamado(this.chamadoForm.value).subscribe({
      next: (res) => {
        this.resultado = res;
        this.loading = false;
        this.chamadoForm.reset({
          torre: 'Torre A',
          apartamento: '',
          titulo: '',
          descricao: ''
        });
      },
      error: (err) => {
        this.erroMsg = 'Falha ao conectar com o servidor de triagem. Verifique se a API FastAPI está ativa.';
        this.loading = false;
      }
    });
  }
}
