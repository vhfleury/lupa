// Estado da sessão corrente, recarregado do servidor a cada navegação.
import { chamar, ErroApi, type OpcoesChamada } from './api';
import { consumirMarcador, marcarSessao } from './marcador';
import type { Permissao, Sessao } from './tipos';
import { visualizacao } from './visualizacao.svelte';

let atual = $state<Sessao | null>(null);

export const sessao = {
  get atual(): Sessao | null {
    return visualizacao.projetar(atual);
  },
  get real(): Sessao | null {
    return atual;
  },
  definir(nova: Sessao | null): void {
    if (!nova || nova.usuario_id !== atual?.usuario_id || nova.papel !== atual?.papel || nova.troca_senha_obrigatoria) visualizacao.encerrar();
    atual = nova;
  },
};

/** Busca a sessão no servidor; devolve null se não houver sessão válida. */
export async function carregarSessao(executar?: typeof fetch): Promise<Sessao | null> {
  const opcoes: OpcoesChamada = { tratarSessao: false };
  if (executar) opcoes.fetch = executar;
  try {
    const nova = await chamar<Sessao>('GET', '/auth/sessao', undefined, opcoes);
    sessao.definir(nova);
    marcarSessao();
    return nova;
  } catch (erro) {
    if (erro instanceof ErroApi && erro.status === 401) {
      sessao.definir(null);
      return null;
    }
    throw erro;
  }
}

/**
 * Saída voluntária: encerra a sessão no servidor e esquece a local. Apaga o marcador, para o
 * próximo login não falar em sessão expirada. Falha no logout não impede a saída.
 */
export async function encerrarSessao(): Promise<void> {
  try {
    await chamar('POST', '/auth/logout', undefined, { tratarSessao: false });
  } catch {
    // Sessão já inválida no servidor: basta esquecer a local.
  }
  consumirMarcador();
  sessao.definir(null);
}

export function tem(s: Sessao | null, permissao: Permissao): boolean {
  return s !== null && s.permissoes.includes(permissao);
}
