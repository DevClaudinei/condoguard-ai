export type UrgenciaEnum = 'P1_CRITICO' | 'P2_URGENTE' | 'P3_ROTINA';

export interface ChamadoCreate {
  torre: string;
  apartamento: string;
  titulo: string;
  descricao: string;
}

export interface ChamadoResponse {
  chamado_id: string;
  torre: string;
  apartamento: string;
  titulo: string;
  descricao: string;
  urgencia: UrgenciaEnum;
  score_confianca: number;
  notificado: boolean;
  duplicado?: boolean;
  parent_id?: string | null;
  mensagem_alerta?: string | null;
}
