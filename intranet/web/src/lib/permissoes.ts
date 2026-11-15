import type { Sessao, Usuario } from './tipos';

export interface AcoesSobre {
  gerir: boolean;
  resetar: boolean;
}

export function acoesSobre(sessao: Sessao | null, usuario: Usuario): AcoesSobre {
  if (!sessao || usuario.id === sessao.usuario_id || usuario.papel !== 'assessor') {
    return { gerir: false, resetar: false };
  }
  return {
    gerir: sessao.permissoes.includes('gerir_assessor'),
    resetar: sessao.permissoes.includes('resetar_assessor'),
  };
}

export function gereUsuarios(sessao: Sessao | null): boolean {
  return sessao?.permissoes.includes('gerir_assessor') ?? false;
}
