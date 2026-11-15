import { describe, expect, it } from 'vitest';
import {
  ACOES,
  FILTROS_VAZIOS,
  formatarDinheiro,
  formatarInstante,
  linkExportacao,
  linkRelatorio,
  montarQuery,
  textoVerificacao,
  validarFiltros,
} from './auditoria';

const ID = '0f'.repeat(32);

describe('filtros da auditoria', () => {
  it('query leva só os campos preenchidos e os extras', () => {
    expect(montarQuery(FILTROS_VAZIOS)).toBe('');
    const query = montarQuery(
      { ...FILTROS_VAZIOS, usuario_id: ID, ip: ' 10.0.0.1 ' },
      {
        limite: '50',
      },
    );
    const busca = new URLSearchParams(query.slice(1));
    expect(busca.get('usuario_id')).toBe(ID);
    expect(busca.get('ip')).toBe('10.0.0.1');
    expect(busca.get('limite')).toBe('50');
    expect(busca.has('acao')).toBe(false);
  });

  it('intervalo vira instante ISO', () => {
    const query = montarQuery({ ...FILTROS_VAZIOS, inicio: '2026-01-01T10:00' });
    const inicio = new URLSearchParams(query.slice(1)).get('inicio') ?? '';
    expect(new Date(inicio).getTime()).toBe(new Date('2026-01-01T10:00').getTime());
  });

  it('valida identificadores e a ordem do intervalo', () => {
    expect(validarFiltros(FILTROS_VAZIOS)).toBeNull();
    expect(validarFiltros({ ...FILTROS_VAZIOS, usuario_id: ID })).toBeNull();
    expect(validarFiltros({ ...FILTROS_VAZIOS, processo_id: 'xyz' })).toMatch(/processo/);
    expect(
      validarFiltros({ ...FILTROS_VAZIOS, inicio: '2026-02-01T00:00', fim: '2026-01-01T00:00' }),
    ).toMatch(/anterior/);
  });

  it('exportação aponta para a API com o formato', () => {
    expect(linkExportacao(FILTROS_VAZIOS, 'csv')).toBe('/api/auditoria/exportar?formato=csv');
    expect(linkExportacao({ ...FILTROS_VAZIOS, acao: 'login_ok' }, 'json')).toContain(
      'acao=login_ok',
    );
  });

  it('CSV de uso filtra pelo processo, usuário e período da consulta', () => {
    const link = new URL(
      linkRelatorio({
        ...FILTROS_VAZIOS,
        processo_id: ID,
        usuario_id: ID,
        inicio: '2026-01-01T10:00',
        fim: '2026-01-02T10:00',
        acao: 'login_ok',
      }),
      'https://lupa.test',
    );
    expect(link.pathname).toBe('/api/auditoria/relatorio-uso');
    expect(Object.fromEntries(link.searchParams)).toEqual({
      formato: 'csv',
      processo: ID,
      usuario: ID,
      inicio: new Date('2026-01-01T10:00').toISOString(),
      fim: new Date('2026-01-02T10:00').toISOString(),
    });
  });

  it('lista de ações inclui a revisão de processo', () => {
    expect(ACOES).toContain('processo_em_revisao');
    expect(ACOES).toContain('revisao_liberada');
  });
});

describe('textos', () => {
  it('verificação íntegra e quebrada', () => {
    const base = { total: 3, primeira_sequencia_quebrada: null, motivo: null };
    expect(textoVerificacao({ ...base, integra: true })).toMatch(/íntegra: 3/);
    expect(
      textoVerificacao({ ...base, integra: false, primeira_sequencia_quebrada: 9, motivo: 'hash' }),
    ).toBe('Cadeia QUEBRADA a partir da sequência 9 (hash).');
  });

  it('instante e dinheiro', () => {
    expect(formatarInstante(null)).toBe('—');
    expect(formatarInstante('2026-01-01T00:00:00Z')).not.toBe('—');
    expect(formatarDinheiro('4.0000', 'USD')).toMatch(/4,00/);
  });
});

describe('menu', () => {
  it('Auditoria aparece só para quem tem ver_auditoria', async () => {
    const { render, screen } = await import('@testing-library/svelte');
    const { default: MenuLateral } = await import('$lib/componentes/MenuLateral.svelte');
    const base = {
      usuario_id: '1',
      nome_usuario: 'x',
      papel: 'desembargador' as const,
      troca_senha_obrigatoria: false,
    };
    render(MenuLateral, { sessao: { ...base, permissoes: ['ver_auditoria'] }, caminho: '/' });
    expect(screen.getByRole('link', { name: 'Auditoria' })).toHaveAttribute('href', '/auditoria');
  });
});
