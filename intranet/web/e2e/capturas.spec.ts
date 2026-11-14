// Etapa 7.9: capturas de tela reais para docs/guias/guia-assessor.md e docs/guias/guia-desembargador.md, sobre
// os processos SINTÉTICOS do E2E (nenhum dado real). Grava PNGs em LUPA_CAPTURAS_DIR (bind mount
// do host feito por intranet/web/scripts/capturas.sh). Não faz asserções de regra: só navega e fotografa.
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { primeiroAcesso } from './testes/acesso';
import { contextoComo } from './testes/credenciais';

const SAIDA = process.env['LUPA_CAPTURAS_DIR'] ?? '/capturas';
const PROCESSO = process.env['LUPA_E2E_PROC_ID'] ?? '';
const CHAT = process.env['LUPA_E2E_CHAT_PROCESSO'] ?? '';

async function foto(page: Page, nome: string): Promise<void> {
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: join(SAIDA, `${nome}.png`), animations: 'disabled', scale: 'css' });
}

test.describe.serial('capturas dos guias', () => {
  test('tela de entrada', async ({ browser }) => {
    const contexto = await browser.newContext();
    const page = await contexto.newPage();
    await page.goto('/login');
    await expect(page.getByLabel('Usuário')).toBeVisible();
    await foto(page, 'login');
    await contexto.close();
  });

  test('telas do assessor', async ({ browser }) => {
    const contexto = await browser.newContext();
    const page = await contexto.newPage();
    await primeiroAcesso(
      page,
      process.env['LUPA_E2E_PROC_USUARIO'] ?? '',
      process.env['LUPA_E2E_PROC_SENHA'] ?? '',
    );
    await page.goto('/processos');
    await expect(page.getByRole('link', { name: /\d{7}-\d{2}/ }).first()).toBeVisible();
    await foto(page, 'processos');
    await page.goto(`/processos/${PROCESSO}`);
    await expect(page.getByRole('heading', { name: 'Enviar autos' })).toBeVisible();
    await foto(page, 'processo');
    await page.goto(`/processos/${PROCESSO}/dossie`);
    await expect(page.getByTestId('indice-pecas').locator('tbody tr').first()).toBeVisible();
    await foto(page, 'dossie');
    await page.getByTestId('evento').first().click();
    await expect(page.getByTestId('destaque-evidencia').first()).toBeVisible();
    await foto(page, 'visualizador');
    await page.goto(`/processos/${PROCESSO}/validacoes`);
    await expect(page.getByTestId('achado').first()).toBeVisible();
    await foto(page, 'validacoes');
    await page
      .getByTestId('achado')
      .first()
      .getByRole('button', { name: 'Corrigir' })
      .first()
      .click();
    await expect(page.getByLabel('Valor corrigido')).toBeVisible();
    await foto(page, 'corrigir-fato');
    await contexto.close();
  });

  test('telas do desembargador', async ({ browser }) => {
    const { contexto, page } = await contextoComo(browser, 'desembargador');
    await page.goto(`/processos/${CHAT}/chat`);
    await expect(page.getByRole('heading', { name: 'Chat sobre os autos' })).toBeVisible();
    const campo = page.getByLabel('Pergunta', { exact: true });
    await campo.fill('Quando a parte apelada foi intimada?');
    await page.getByRole('button', { name: 'Perguntar' }).click();
    await expect(page.getByTestId('citacao')).toBeVisible();
    await campo.fill('Como devo votar neste recurso?');
    await page.getByRole('button', { name: 'Perguntar' }).click();
    await expect(page.getByTestId('mensagem').last()).toHaveAttribute('data-status', 'recusa');
    await foto(page, 'chat');
    await page.goto('/auditoria');
    await expect(page.getByTestId('evento').first()).toBeVisible();
    await foto(page, 'auditoria');
    await page.getByLabel('Por').selectOption('processo');
    await page.getByLabel('Identificador').fill(CHAT);
    await page.getByRole('button', { name: 'Gerar relatório' }).click();
    await expect(page.getByTestId('custo-estimado')).toBeVisible();
    await page.getByTestId('custo-estimado').evaluate((el) => el.scrollIntoView({ block: 'end' }));
    await expect(page.getByTestId('custo-estimado')).toBeInViewport();
    await foto(page, 'relatorio-uso');
    await page.goto('/usuarios');
    await expect(page.getByTestId('linha-usuario').first()).toBeVisible();
    await foto(page, 'usuarios');
    await contexto.close();
  });
});
