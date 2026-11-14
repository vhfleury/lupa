import { expect, test } from '@playwright/test';
import { contextoComo, lerConta } from './credenciais';

test.describe.serial('6.10 auditoria do desembargador e sessão', () => {
  test('o filtro de processo também delimita a exportação de uso em CSV', async ({ browser }) => {
    const { contexto, page } = await contextoComo(browser, 'desembargador');
    const processo = process.env['LUPA_E2E_CHAT_PROCESSO'] ?? '';
    expect(processo).toMatch(/^[0-9a-f]{64}$/);
    try {
      await page.goto('/auditoria');
      await page.getByLabel('Processo (id)').fill(processo);
      await page.getByRole('button', { name: 'Consultar' }).click();
      await expect(page.getByTestId('evento').first()).toBeVisible();
      const exportacao = page.getByRole('link', {
        name: 'Exportar uso por processo e usuário em CSV',
      });
      await expect(exportacao).toHaveAttribute('href', new RegExp(processo));
      const resposta = await page.request.get((await exportacao.getAttribute('href')) ?? '');
      expect(resposta.status()).toBe(200);
      expect(resposta.headers()['content-type']).toContain('text/csv');
      const [cabecalho, ...linhas] = (await resposta.text()).trim().split(/\r?\n/);
      expect(cabecalho).toContain('processo');
      expect(cabecalho).toContain('custo');
      expect(linhas.length).toBeGreaterThan(0);
      for (const linha of linhas) expect(linha).toContain(processo);
    } finally {
      await contexto.close();
    }
  });

  test('relatório por usuário traz o custo estimado (chat e resumos do dossiê)', async ({
    browser,
  }) => {
    const { contexto, page } = await contextoComo(browser, 'desembargador');
    try {
      const desembargador = lerConta('desembargador').usuario;
      const usuarios = (await (await page.request.get('/api/usuarios')).json()) as {
        id: string;
        nome_usuario: string;
      }[];
      const alvo = usuarios.find((u) => u.nome_usuario === desembargador);
      expect(alvo, 'desembargador do chat').toBeDefined();
      await page.goto('/auditoria');
      await page.getByLabel('Por').selectOption('usuario');
      await page.getByLabel('Identificador').fill(alvo?.id ?? '');
      await page.getByRole('button', { name: 'Gerar relatório' }).click();
      await expect(page.getByTestId('relatorio-uso')).toContainText('pergunta_chat');
      await expect(page.getByTestId('custo-estimado')).toContainText('Custo estimado');
      await expect(page.getByTestId('custo-estimado')).toContainText('tokens de entrada');
    } finally {
      await contexto.close();
    }
  });

  test('recarga completa sem sessão avisa "sessão encerrada ou expirada"', async ({ browser }) => {
    const { contexto, page } = await contextoComo(browser, 'desembargador');
    try {
      await page.goto('/usuarios');
      await expect(page.getByRole('heading', { name: 'Usuários' })).toBeVisible();
      // A sessão some (expirou ou foi revogada) e o usuário recarrega a página inteira: a memória
      // da SPA se perde, mas o marcador em sessionStorage diz que havia sessão neste separador.
      await contexto.clearCookies();
      await page.reload();
      await expect(page).toHaveURL(/\/login\?motivo=expirada$/);
      await expect(page.getByRole('status')).toContainText('Sessão encerrada ou expirada');
      // O marcador é consumido (aviso uma vez só) e nunca guarda dado da sessão.
      expect(await page.evaluate(() => sessionStorage.getItem('lupa.sessao-anterior'))).toBeNull();
      const chaves = await page.evaluate(() => Object.keys(sessionStorage));
      expect(chaves.filter((c) => c.startsWith('lupa.'))).toEqual([]);
    } finally {
      await contexto.close();
    }
    // Quem nunca entrou neste separador vê o login sem aviso.
    const novo = await browser.newContext();
    const pagina = await novo.newPage();
    await pagina.goto('/usuarios');
    await expect(pagina).toHaveURL(/\/login$/);
    await expect(pagina.getByText('Sessão encerrada ou expirada')).toHaveCount(0);
    await novo.close();
  });

  test('sair de propósito não mostra aviso de expiração, nem após recarregar', async ({
    browser,
  }) => {
    const { contexto, page } = await contextoComo(browser, 'desembargador');
    try {
      await page.goto('/');
      await page.getByRole('button', { name: 'Sair' }).click();
      await expect(page).toHaveURL(/\/login$/);
      await page.reload();
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.getByText('Sessão encerrada ou expirada')).toHaveCount(0);
    } finally {
      await contexto.close();
    }
  });
});
