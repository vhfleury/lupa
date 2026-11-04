import type { Permissao, Sessao } from './tipos';

export type PerfilVisualizacao = 'assessor' | 'desembargador';
let perfil = $state<PerfilVisualizacao | null>(null);
const permissoes: Record<PerfilVisualizacao, Permissao[]> = {
  assessor: ['ver_processo', 'subir_processo', 'anotar'],
  desembargador: ['ver_processo', 'subir_processo', 'anotar', 'ver_auditoria', 'gerir_assessor', 'resetar_assessor'],
};

export const visualizacao = {
  get ativa(): boolean { return perfil !== null; },
  get perfil(): PerfilVisualizacao | null { return perfil; },
  iniciar(sessao: Sessao | null, alvo: PerfilVisualizacao = 'assessor'): void {
    const permitido = sessao !== null && !sessao.troca_senha_obrigatoria &&
      (sessao.papel === 'administrador' || (sessao.papel === 'desembargador' && alvo === 'assessor'));
    perfil = permitido ? alvo : null;
  },
  encerrar(): void { perfil = null; },
  permiteRota(caminho: string): boolean {
    return perfil === null || caminho === '/' || /^\/processos(?:\/|$)/.test(caminho) ||
      (perfil === 'desembargador' && /^\/(usuarios|auditoria)(?:\/|$)/.test(caminho));
  },
  projetar(sessao: Sessao | null): Sessao | null {
    if (!perfil || !sessao) return sessao;
    const permitidas = permissoes[perfil];
    return { ...sessao, papel: perfil, permissoes: sessao.permissoes.filter(p => permitidas.includes(p)) };
  },
};
