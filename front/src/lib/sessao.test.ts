import { afterEach, describe, expect, it, vi } from 'vitest';
import { CHAVE_MARCADOR, marcarSessao } from './marcador';
import { encerrarSessao, sessao } from './sessao.svelte';
import type { Sessao } from './tipos';

const assessor: Sessao = {
  usuario_id: 'u1',
  nome_usuario: 'ana',
  papel: 'assessor',
  gabinete_id: 'g1',
  troca_senha_obrigatoria: true,
  permissoes: ['ver_processo'],
};

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
  sessao.definir(null);
});

describe('encerrarSessao', () => {
  it('chama o logout, apaga o marcador e limpa a sessão', async () => {
    const executar = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', executar);
    sessao.definir(assessor);
    marcarSessao();

    await encerrarSessao();

    expect(executar).toHaveBeenCalledWith(
      '/api/auth/logout',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(sessionStorage.getItem(CHAVE_MARCADOR)).toBeNull();
    expect(sessao.real).toBeNull();
  });

  it('saída voluntária com logout falhando ainda apaga o marcador e limpa a sessão', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('{"detail":"não autenticado"}', { status: 401 })),
    );
    sessao.definir(assessor);
    marcarSessao();

    await encerrarSessao();

    expect(sessionStorage.getItem(CHAVE_MARCADOR)).toBeNull();
    expect(sessao.real).toBeNull();
  });
});
