import { render, screen } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import Chat from '../../routes/processos/[id]/chat/+page.svelte';

vi.mock('$app/state', () => ({ page: { params: { id: 'ab'.repeat(32) } } }));
afterEach(() => vi.unstubAllGlobals());

it('RF-CHA-06 encerra a entrada de perguntas quando a última conversa alcança seu teto', async () => {
  vi.stubGlobal('fetch', async (url: string) =>
    Response.json(
      url.includes('/chat')
        ? {
            conversas: [
              {
                conversa_id: '01'.repeat(32),
                criada_em: '2026-01-01T10:00:00Z',
                encerrada: true,
                motivo_encerramento: 'teto_conversa',
                mensagens: [],
                citacoes_descartadas: 0,
              },
            ],
          }
        : { em_revisao: false },
    ),
  );
  render(Chat);
  const campo = await screen.findByRole('textbox', { name: 'Pergunta' });
  expect(campo).toBeDisabled();
  expect(
    screen.getByText('Limite de uso da conversa atingido.', { exact: true }),
  ).toBeInTheDocument();
});
