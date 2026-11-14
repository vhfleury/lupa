import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { sessao } from '$lib/sessao.svelte';
import Validacoes from '../../routes/processos/[id]/validacoes/+page.svelte';

vi.mock('$app/state', () => ({ page: { params: { id: 'ab'.repeat(32) } } }));

const fatoId = '01'.repeat(32);
const pagina = '02'.repeat(32);
const fonte = {
  id: '03'.repeat(32),
  pagina_id: pagina,
  arquivo_id: '04'.repeat(32),
  pagina: 3,
  inicio: 8,
  fim: 18,
  trecho: '2025-04-03',
};

afterEach(() => {
  sessao.definir(null);
  vi.unstubAllGlobals();
});

function montar(): unknown[] {
  const enviados: unknown[] = [];
  const fato = {
    id: fatoId,
    tipo: 'data_intimacao',
    valor: '2025-04-03',
    status: 'automatico',
    vigente: true,
    criado_em: '2025-04-06T12:00:00Z',
    evidencias: [fonte],
  };
  const achado = {
    id: '05'.repeat(32),
    validacao: 'tempestividade_recurso',
    resultado: 'conforme',
    explicacao: 'Confira a intimação.',
    valores: {},
    fatos_usados: [fatoId],
    vigente: true,
  };
  vi.stubGlobal('fetch', async (url: string, init: RequestInit) => {
    if (init.method === 'POST') {
      enviados.push(JSON.parse(String(init.body)));
      return Response.json({ achados_gravados: 1 });
    }
    if (url.endsWith('/anotacoes')) return Response.json({ anotacoes: [] });
    if (url.includes('/fatos')) return Response.json({ fatos: [fato] });
    return Response.json({ achados: [achado] });
  });
  sessao.definir({
    usuario_id: '07'.repeat(32),
    nome_usuario: 'assessora',
    papel: 'assessor',
    permissoes: ['anotar'],
    troca_senha_obrigatoria: false,
  });
  render(Validacoes);
  return enviados;
}

it('RF-FAT-03 envia página, intervalo e trecho ao corrigir o valor', async () => {
  const enviados = montar();
  await fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }));
  await fireEvent.input(screen.getByLabelText('Valor corrigido'), {
    target: { value: '2025-04-04' },
  });
  await fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }));
  await waitFor(() =>
    expect(enviados).toEqual([
      {
        status: 'corrigido',
        valor: '2025-04-04',
        pagina_id: pagina,
        inicio: 8,
        fim: 18,
        trecho: '2025-04-03',
      },
    ]),
  );
});

it('RF-FAT-03 confirma o fato sem substituir valor ou evidência', async () => {
  const enviados = montar();
  await fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }));
  await waitFor(() => expect(enviados).toEqual([{ status: 'confirmado' }]));
});

it('RF-FAT-03 aceita o trecho literal de outra página dos autos', async () => {
  const enviados = montar();
  await fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }));
  await fireEvent.change(screen.getByLabelText('Fonte da correção'), { target: { value: '' } });
  const outra = '09'.repeat(32);
  await fireEvent.input(screen.getByLabelText('Identificador da página'), {
    target: { value: outra },
  });
  await fireEvent.input(screen.getByLabelText(/Início do trecho/), { target: { value: '20' } });
  await fireEvent.input(screen.getByLabelText(/Fim do trecho/), { target: { value: '30' } });
  await fireEvent.input(screen.getByLabelText('Trecho literal dos autos'), {
    target: { value: '2025-04-04' },
  });
  await fireEvent.input(screen.getByLabelText('Valor corrigido'), {
    target: { value: '2025-04-04' },
  });
  await fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }));
  await waitFor(() =>
    expect(enviados).toEqual([
      {
        status: 'corrigido',
        valor: '2025-04-04',
        pagina_id: outra,
        inicio: 20,
        fim: 30,
        trecho: '2025-04-04',
      },
    ]),
  );
});
