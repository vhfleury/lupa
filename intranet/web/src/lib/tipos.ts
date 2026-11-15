// Formatos das respostas da API (intranet/api/src/lupa_intranet/acesso/rotas.py).
export type Papel = 'assessor' | 'desembargador';

export type Permissao =
  | 'ver_processo'
  | 'subir_processo'
  | 'anotar'
  | 'ver_auditoria'
  | 'gerir_assessor'
  | 'resetar_assessor';

export interface Sessao {
  usuario_id: string;
  nome_usuario: string;
  papel: Papel;
  troca_senha_obrigatoria: boolean;
  permissoes: Permissao[];
}

export interface Usuario {
  id: string;
  nome_usuario: string;
  papel: Papel;
  ativo: boolean;
  mfa_confirmado: boolean;
  troca_senha_obrigatoria: boolean;
}

export interface UsuarioComSenha extends Usuario {
  senha_temporaria: string;
}

export type RespostaLogin =
  | { etapa: 'mfa'; desafio: string }
  | { etapa: 'configurar_mfa'; desafio: string; segredo: string; uri_qr: string };

export interface RespostaMfa {
  troca_senha_obrigatoria: boolean;
}

export const ROTULO_PAPEL: Record<Papel, string> = {
  assessor: 'Assessor',
  desembargador: 'Desembargador',
};
