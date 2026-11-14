// Fluxos ponta a ponta das subetapas 6.1 a 6.3 contra a API real (pelo proxy, mesmo origin).
// O desembargador vem de e2e_preparar.py e cria o assessor pela interface.
import { randomBytes } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { enviarSenha, entrar, primeiroAcesso, senhaNova } from './acesso';
import { guardarConta, type Conta } from './credenciais';
import { Autenticador, segredoDaUri } from './totp';

const DESEMBARGADOR = process.env['LUPA_E2E_DES_USUARIO'] ?? '';
const SENHA_TEMPORARIA = process.env['LUPA_E2E_DES_SENHA'] ?? '';
const SUFIXO = randomBytes(3).toString('hex');
const ASSESSOR = `ass.e2e.${SUFIXO}`;
const MENSAGEM_CREDENCIAIS = 'Usuário ou senha inválidos.';
const MENSAGEM_BLOQUEIO = /Muitas tentativas/;

const contas: Record<string, Conta> = {};
let senhaTemporariaAssessor = '';

function conta(nome: string): Conta {
  const encontrada = contas[nome];
  if (!encontrada) throw new Error(`conta ${nome} ainda não criada`);
  return encontrada;
}

async function sair(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Sair' }).click();
  await expect(page).toHaveURL(/\/login$/);
}

async function lerSenhaTemporaria(page: Page): Promise<string> {
  const valor = ((await page.getByTestId('senha-temporaria-valor').textContent()) ?? '').trim();
  expect(valor.length).toBeGreaterThanOrEqual(12);
  await expect(page.getByText('não será exibida de novo')).toBeVisible();
  await page.getByRole('button', { name: /Já anotei/ }).click();
  await expect(page.getByTestId('senha-temporaria')).toHaveCount(0);
  await expect(page.getByText(valor)).toHaveCount(0);
  return valor;
}

async function alerta(page: Page): Promise<string> {
  const elemento = page.getByRole('alert');
  await expect(elemento).toBeVisible();
  return ((await elemento.textContent()) ?? '').trim();
}

function linha(page: Page, usuario: string) {
  return page.locator(`tr[data-usuario="${usuario}"]`);
}

test.describe.serial('Etapa 6.1 a 6.3', () => {
  test.beforeAll(() => {
    expect(
      DESEMBARGADOR,
      'rode via intranet/web/scripts/e2e.sh (prepara o desembargador)',
    ).not.toBe('');
    expect(SENHA_TEMPORARIA).not.toBe('');
  });

  // 6.10: o desembargador (dono do primeiro acesso aqui) fica disponível para os testes finais.
  test.afterAll(() => {
    if (contas[DESEMBARGADOR]) guardarConta('desembargador', conta(DESEMBARGADOR));
  });

  test('6.1 rota protegida redireciona para o login e a API responde no mesmo origin', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('form', { name: 'Entrar' })).toBeVisible();
    const saude = await page.request.get('/api/saude');
    expect(saude.status()).toBe(200);
    expect((await page.request.get('/api/auth/sessao')).status()).toBe(401);
  });

  test('6.2 desembargador: primeiro acesso, código errado recusado, troca obrigatória antes de tudo', async ({
    page,
  }) => {
    await enviarSenha(page, DESEMBARGADOR, SENHA_TEMPORARIA);
    await expect(page.getByRole('heading', { name: 'Cadastre o autenticador' })).toBeVisible();
    const segredo = segredoDaUri(((await page.getByTestId('uri-mfa').textContent()) ?? '').trim());
    const autenticador = new Autenticador(segredo);
    await page.getByLabel('Código de 6 dígitos').fill(autenticador.errado());
    await page.getByRole('button', { name: 'Confirmar autenticador' }).click();
    await expect(page.getByRole('alert')).toContainText('Código inválido');
    await page.getByLabel('Código de 6 dígitos').fill(await autenticador.proximo());
    await page.getByRole('button', { name: 'Confirmar autenticador' }).click();
    await expect(page).toHaveURL(/\/trocar-senha$/);

    // Com troca pendente, nenhuma outra tela nem rota da API.
    await page.goto('/usuarios');
    await expect(page).toHaveURL(/\/trocar-senha$/);
    expect((await page.request.get('/api/usuarios')).status()).toBe(403);

    const senha = senhaNova();
    await page.getByLabel('Senha atual').fill(SENHA_TEMPORARIA);
    await page.getByLabel('Nova senha', { exact: true }).fill(senha);
    await page.getByLabel('Confirme a nova senha').fill(senha);
    await page.getByRole('button', { name: 'Salvar nova senha' }).click();
    await expect(page.getByTestId('usuario-papel')).toHaveText('Desembargador');
    await expect(page.getByTestId('estado-sessao')).toContainText('Sessão ativa');
    const menu = page.getByRole('navigation', { name: 'Menu principal' });
    await expect(menu.getByRole('link', { name: 'Usuários' })).toBeVisible();
    await expect(menu.getByRole('link', { name: 'Auditoria' })).toBeVisible();
    contas[DESEMBARGADOR] = { usuario: DESEMBARGADOR, senha, autenticador };
    guardarConta('desembargador', conta(DESEMBARGADOR));
  });

  test('6.3 desembargador cria, desativa, reativa e redefine o acesso do assessor', async ({
    page,
  }) => {
    await entrar(page, conta(DESEMBARGADOR));
    await expect(page.getByTestId('usuario-papel')).toHaveText('Desembargador');
    const menu = page.getByRole('navigation', { name: 'Menu principal' });
    await expect(menu.getByRole('link', { name: 'Gabinetes' })).toHaveCount(0);
    await menu.getByRole('link', { name: 'Usuários' }).click();

    await expect(page.getByRole('heading', { name: 'Novo assessor' })).toBeVisible();
    await expect(page.getByLabel('Papel')).toHaveCount(0);
    await page.getByLabel('Nome de usuário').fill(ASSESSOR);
    await page.getByRole('button', { name: 'Criar assessor' }).click();
    const primeira = await lerSenhaTemporaria(page);

    const linhaAss = linha(page, ASSESSOR);
    await expect(linhaAss.getByTestId('situacao')).toHaveText(/Ativo · troca de senha pendente/);
    // 6.10: desativar pede confirmação; cancelar não muda nada.
    await linhaAss.getByRole('button', { name: `Desativar ${ASSESSOR}` }).click();
    const confirmacao = page.getByRole('dialog', { name: 'Desativar usuário?' });
    await expect(confirmacao).toBeVisible();
    await expect(confirmacao).toContainText(ASSESSOR);
    await expect(confirmacao.getByRole('button', { name: 'Cancelar' })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(confirmacao).toBeHidden();
    await expect(linhaAss.getByTestId('situacao')).toHaveText(/^\s*Ativo/);
    await linhaAss.getByRole('button', { name: `Desativar ${ASSESSOR}` }).click();
    await confirmacao.getByRole('button', { name: 'Desativar' }).click();
    await expect(linhaAss.getByTestId('situacao')).toHaveText(/^\s*Inativo/);
    await linhaAss.getByRole('button', { name: `Reativar ${ASSESSOR}` }).click();
    await expect(linhaAss.getByTestId('situacao')).toHaveText(/^\s*Ativo/);
    await linhaAss.getByRole('button', { name: `Resetar senha de ${ASSESSOR}` }).click();
    senhaTemporariaAssessor = await lerSenhaTemporaria(page);
    expect(senhaTemporariaAssessor).not.toBe(primeira);
    await linhaAss.getByRole('button', { name: `Resetar autenticador de ${ASSESSOR}` }).click();
    await expect(page.getByRole('status')).toContainText('autenticador apagado');
    // Sobre si mesmo, nenhuma ação.
    await expect(linha(page, DESEMBARGADOR).getByRole('button')).toHaveCount(0);
  });

  test('6.3 gestão pela API permite ao desembargador criar apenas assessores', async ({ page }) => {
    await entrar(page, conta(DESEMBARGADOR));
    const desembargadorNovo = await page.request.post('/api/usuarios', {
      data: { nome_usuario: `des.pirata.${SUFIXO}`, papel: 'desembargador' },
    });
    expect(desembargadorNovo.status()).toBe(403);
    await sair(page);
  });

  test('6.2/6.3 assessor: primeiro acesso após reset; sem telas de gestão; servidor nega', async ({
    page,
  }) => {
    contas[ASSESSOR] = await primeiroAcesso(page, ASSESSOR, senhaTemporariaAssessor);
    await expect(page.getByTestId('usuario-papel')).toHaveText('Assessor');
    const menu = page.getByRole('navigation', { name: 'Menu principal' });
    await expect(menu.getByRole('link')).toHaveText(['Início', 'Processos']); // Processos: 6.4
    await page.goto('/usuarios');
    await expect(page.getByRole('alert')).toContainText('não dá acesso');
    expect((await page.request.get('/api/usuarios')).status()).toBe(403);
    const criar = await page.request.post('/api/usuarios', {
      data: { nome_usuario: `ass.pirata.${SUFIXO}`, papel: 'assessor' },
    });
    expect(criar.status()).toBe(403);
  });

  test('6.2 sessão expirada volta ao login com aviso', async ({ page, context }) => {
    await entrar(page, conta(DESEMBARGADOR));
    // Simula a expiração no servidor: o navegador deixa de ter uma sessão válida e a próxima
    // navegação descobre isso ao conferir a sessão.
    await context.clearCookies();
    await page
      .getByRole('navigation', { name: 'Menu principal' })
      .getByRole('link', { name: 'Usuários' })
      .click();
    await expect(page).toHaveURL(/\/login\?motivo=expirada$/);
    await expect(page.getByRole('status')).toContainText('Sessão encerrada ou expirada');
  });

  test('6.2 mensagens idênticas e bloqueio após 5 falhas sem revelar se o usuário existe', async ({
    page,
  }) => {
    const fantasma = `ninguem.${SUFIXO}`;
    await enviarSenha(page, ASSESSOR, 'senha-errada-de-proposito');
    const existente = await alerta(page);
    await enviarSenha(page, fantasma, 'senha-errada-de-proposito');
    const inexistente = await alerta(page);
    expect(existente).toBe(MENSAGEM_CREDENCIAIS);
    expect(inexistente).toBe(existente);

    for (let i = 0; i < 4; i++) {
      await enviarSenha(page, fantasma, 'senha-errada-de-proposito');
      await expect(page.getByRole('alert')).toHaveText(MENSAGEM_CREDENCIAIS);
      await enviarSenha(page, ASSESSOR, 'senha-errada-de-proposito');
      await expect(page.getByRole('alert')).toHaveText(MENSAGEM_CREDENCIAIS);
    }
    await enviarSenha(page, fantasma, 'senha-errada-de-proposito');
    const bloqueioInexistente = await alerta(page);
    // Nem a senha certa entra durante o bloqueio, e a mensagem é a mesma.
    await enviarSenha(page, ASSESSOR, conta(ASSESSOR).senha);
    const bloqueioExistente = await alerta(page);
    expect(bloqueioInexistente).toMatch(MENSAGEM_BLOQUEIO);
    expect(bloqueioExistente).toBe(bloqueioInexistente);
  });
});
