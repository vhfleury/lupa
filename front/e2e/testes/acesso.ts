// Passos de login pela tela, comuns a todos os arquivos de teste: primeiro acesso (senha
// temporária, cadastro do autenticador e troca de senha) e entrada com senha e TOTP.
import { randomBytes } from 'node:crypto';
import { expect, type Page } from '@playwright/test';
import type { Conta } from './credenciais';
import { Autenticador, segredoDaUri } from './totp';

export function senhaNova(): string {
  return `frase-e2e-${randomBytes(9).toString('base64url')}-lupa`;
}

/** Abre o login e envia usuário e senha (primeiro passo). */
export async function enviarSenha(page: Page, usuario: string, senha: string): Promise<void> {
  await page.goto('/login');
  await page.getByLabel('Usuário').fill(usuario);
  await page.getByLabel('Senha', { exact: true }).fill(senha);
  await page.getByRole('button', { name: 'Continuar' }).click();
}

/** Primeiro acesso completo de uma conta com senha temporária; devolve a conta já pronta. */
export async function primeiroAcesso(page: Page, usuario: string, temporaria: string): Promise<Conta> {
  await enviarSenha(page, usuario, temporaria);
  await expect(page.getByRole('heading', { name: 'Cadastre o autenticador' })).toBeVisible();
  await expect(page.getByRole('img', { name: /QR code para cadastrar/ })).toBeVisible();
  const uri = (await page.getByTestId('uri-mfa').textContent()) ?? '';
  const segredo = segredoDaUri(uri.trim());
  await expect(page.getByTestId('segredo-mfa')).toHaveText(segredo);
  const autenticador = new Autenticador(segredo);
  await page.getByLabel('Código de 6 dígitos').fill(await autenticador.proximo());
  await page.getByRole('button', { name: 'Confirmar autenticador' }).click();
  await expect(page).toHaveURL(/\/trocar-senha$/);
  await expect(page.getByText(/defina uma senha pessoal/)).toBeVisible();
  const senha = senhaNova();
  await page.getByLabel('Senha atual').fill(temporaria);
  await page.getByLabel('Nova senha', { exact: true }).fill(senha);
  await page.getByLabel('Confirme a nova senha').fill(senha);
  await page.getByRole('button', { name: 'Salvar nova senha' }).click();
  await expect(page.getByTestId('usuario-nome')).toHaveText(usuario);
  return { usuario, senha, autenticador };
}

/** Entrada com senha e código TOTP de uma conta que já fez o primeiro acesso. */
export async function entrar(page: Page, conta: Conta): Promise<void> {
  await enviarSenha(page, conta.usuario, conta.senha);
  await expect(page.getByRole('heading', { name: 'Verificação em duas etapas' })).toBeVisible();
  await page.getByLabel('Código de 6 dígitos').fill(await conta.autenticador.proximo());
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page.getByTestId('usuario-nome')).toHaveText(conta.usuario);
}
