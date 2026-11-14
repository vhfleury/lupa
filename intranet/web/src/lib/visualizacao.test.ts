import { afterEach, describe, expect, it, vi } from 'vitest';
import { visualizacao } from './visualizacao.svelte';
import { sessao } from './sessao.svelte';
import { chamar } from './api';
import type { Sessao } from './tipos';

const juiz: Sessao = {
  usuario_id: 'juiz',
  nome_usuario: 'juiz',
  papel: 'desembargador',
  troca_senha_obrigatoria: false,
  permissoes: ['ver_processo', 'subir_processo', 'anotar', 'ver_auditoria'],
};
afterEach(() => {
  sessao.definir(null);
  visualizacao.encerrar();
});

describe('visualização como assessor', () => {
  it('restringe a prévia às rotas do assessor (RF-ACE-03)', () => {
    visualizacao.iniciar(juiz);
    expect(visualizacao.permiteRota('/processos')).toBe(true);
    expect(visualizacao.permiteRota('/usuarios')).toBe(false);
    expect(visualizacao.permiteRota('/auditoria')).toBe(false);
  });
  it('projeta controles sem mudar a identidade real e restaura o perfil ao sair', () => {
    sessao.definir(juiz);
    visualizacao.iniciar(sessao.real);
    expect(sessao.atual?.papel).toBe('assessor');
    expect(sessao.atual?.permissoes).toEqual(['ver_processo', 'subir_processo', 'anotar']);
    expect(sessao.real).toEqual(juiz);
    sessao.definir({ ...juiz });
    expect(visualizacao.ativa).toBe(true);
    visualizacao.encerrar();
    expect(sessao.atual?.papel).toBe('desembargador');
  });
  it('impede ativação por assessor e encerra na troca ou expiração da sessão', () => {
    visualizacao.iniciar({ ...juiz, papel: 'assessor' });
    expect(visualizacao.ativa).toBe(false);
    sessao.definir(juiz);
    visualizacao.iniciar(juiz);
    sessao.definir({ ...juiz, usuario_id: 'outro' });
    expect(visualizacao.ativa).toBe(false);
    visualizacao.iniciar(sessao.real);
    sessao.definir(null);
    expect(visualizacao.ativa).toBe(false);
  });
  it('bloqueia alterações antes de enviar à API e permite sair da conta', async () => {
    visualizacao.iniciar(juiz);
    const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    await expect(chamar('POST', '/processos', {}, { fetch })).rejects.toThrow(/Encerre/);
    expect(fetch).not.toHaveBeenCalled();
    await chamar('POST', '/auth/logout', undefined, { fetch });
    expect(fetch).toHaveBeenCalledOnce();
  });
});
