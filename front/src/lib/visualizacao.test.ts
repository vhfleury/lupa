import { afterEach, describe, expect, it, vi } from 'vitest';
import { visualizacao } from './visualizacao.svelte';
import { sessao } from './sessao.svelte';
import { chamar } from './api';
import type { Sessao } from './tipos';

const admin: Sessao = {
  usuario_id: 'admin', nome_usuario: 'admin', papel: 'administrador',
  gabinete_id: null, troca_senha_obrigatoria: false,
  permissoes: ['ver_processo', 'subir_processo', 'anotar', 'gerir_gabinetes', 'ver_auditoria'],
};
afterEach(() => { sessao.definir(null); visualizacao.encerrar(); });

describe('visualização como assessor', () => {
  it('admin visualiza desembargador com rotas próprias e sem gestão de gabinetes', () => {
    visualizacao.iniciar(admin, 'desembargador');
    expect(visualizacao.perfil).toBe('desembargador');
    expect(visualizacao.projetar(admin)?.permissoes).toContain('ver_auditoria');
    expect(visualizacao.projetar(admin)?.permissoes).not.toContain('gerir_gabinetes');
    expect(visualizacao.permiteRota('/usuarios')).toBe(true);
    expect(visualizacao.permiteRota('/auditoria')).toBe(true);
    expect(visualizacao.permiteRota('/gabinetes')).toBe(false);
    visualizacao.iniciar(admin, 'assessor');
    expect(visualizacao.permiteRota('/usuarios')).toBe(false);
    visualizacao.iniciar({ ...admin, papel: 'desembargador' }, 'desembargador');
    expect(visualizacao.ativa).toBe(false);
  });
  it('projeta controles sem mudar a identidade real e restaura o perfil ao sair', () => {
    sessao.definir(admin);
    visualizacao.iniciar(sessao.real);
    expect(sessao.atual?.papel).toBe('assessor');
    expect(sessao.atual?.permissoes).toEqual(['ver_processo', 'subir_processo', 'anotar']);
    expect(sessao.real).toEqual(admin);
    sessao.definir({ ...admin });
    expect(visualizacao.ativa).toBe(true);
    visualizacao.encerrar();
    expect(sessao.atual?.papel).toBe('administrador');
  });
  it('impede ativação por assessor e encerra na troca ou expiração da sessão', () => {
    visualizacao.iniciar({ ...admin, papel: 'assessor' });
    expect(visualizacao.ativa).toBe(false);
    sessao.definir(admin);
    visualizacao.iniciar(admin);
    sessao.definir({ ...admin, usuario_id: 'outro' });
    expect(visualizacao.ativa).toBe(false);
    visualizacao.iniciar(sessao.real);
    sessao.definir(null);
    expect(visualizacao.ativa).toBe(false);
  });
  it('bloqueia alterações antes de enviar à API e permite sair da conta', async () => {
    visualizacao.iniciar(admin);
    const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    await expect(chamar('POST', '/processos', {}, { fetch })).rejects.toThrow(/Encerre/);
    expect(fetch).not.toHaveBeenCalled();
    await chamar('POST', '/auth/logout', undefined, { fetch });
    expect(fetch).toHaveBeenCalledOnce();
  });
});
