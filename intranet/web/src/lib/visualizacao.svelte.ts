import type { Permissao, Sessao } from './tipos';

const PERMISSOES_ASSESSOR: Permissao[] = ['ver_processo', 'subir_processo', 'anotar'];
let ativa = $state(false);

export const visualizacao = {
  get ativa(): boolean {
    return ativa;
  },
  get perfil(): 'assessor' | null {
    return ativa ? 'assessor' : null;
  },
  iniciar(sessao: Sessao | null): void {
    ativa = sessao?.papel === 'desembargador' && !sessao.troca_senha_obrigatoria;
  },
  encerrar(): void {
    ativa = false;
  },
  permiteRota(caminho: string): boolean {
    return !ativa || caminho === '/' || /^\/processos(?:\/|$)/.test(caminho);
  },
  projetar(sessao: Sessao | null): Sessao | null {
    if (!ativa || !sessao) return sessao;
    return {
      ...sessao,
      papel: 'assessor',
      permissoes: sessao.permissoes.filter((p) => PERMISSOES_ASSESSOR.includes(p)),
    };
  },
};
