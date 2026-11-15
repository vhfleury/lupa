import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { sessao } from '$lib/sessao.svelte';
import Processos from '../../routes/processos/+page.svelte';
import { digitoVerificador } from './cnj';

afterEach(() => {
  sessao.definir(null);
  vi.unstubAllGlobals();
});

it('envia o número e a classe cível selecionada no cadastro', async () => {
  const numero = `0004321-${digitoVerificador('0004321', '2025', '8', '09', '0001')}.2025.8.09.0001`;
  const requisicoes: RequestInit[] = [];
  vi.stubGlobal('fetch', async (_: RequestInfo, init: RequestInit) => {
    if (init.method === 'POST') {
      requisicoes.push(init);
      return Response.json({
        id: 'ab'.repeat(32),
        numero_cnj: numero,
        classe: 'agravo_instrumento',
      });
    }
    return Response.json([]);
  });
  sessao.definir({
    usuario_id: '01'.repeat(32),
    nome_usuario: 'assessor',
    papel: 'assessor',
    troca_senha_obrigatoria: false,
    permissoes: ['subir_processo'],
  });
  render(Processos);
  await fireEvent.click(screen.getByRole('button', { name: /Novo processo/ }));
  const enviar = screen.getByRole('button', { name: 'Criar processo' });
  expect(enviar).toBeDisabled();
  await fireEvent.input(screen.getByLabelText('Número CNJ'), { target: { value: numero } });
  await fireEvent.change(screen.getByLabelText('Classe'), {
    target: { value: 'agravo_instrumento' },
  });
  await fireEvent.click(enviar);
  expect(await screen.findByText(`Processo ${numero} criado.`)).toBeInTheDocument();
  expect(requisicoes).toHaveLength(1);
  expect(JSON.parse(String(requisicoes[0]?.body))).toEqual({
    numero_cnj: numero,
    classe: 'agravo_instrumento',
  });
});
