import { defineConfig, devices } from '@playwright/test';

// Os fluxos cadastram MFA, trocam senhas e guardam as contas usadas nos testes finais.
const comum = { ...devices['Desktop Chrome'] };

export default defineConfig({
  testDir: './testes',
  globalSetup: './testes/global-setup.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env['LUPA_E2E_URL'] ?? 'https://proxy:8443',
    ignoreHTTPSErrors: true,
    locale: 'pt-BR',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'acesso', testMatch: /fluxos\.spec\.ts$/, use: comum },
    {
      name: 'fluxos',
      testMatch: /(chat-auditoria|processos)\.spec\.ts$/,
      dependencies: ['acesso'],
      use: comum,
    },
    {
      name: 'finais',
      testMatch: /\/(acessibilidade|auditoria|seguranca)\.spec\.ts$/,
      dependencies: ['fluxos'],
      use: comum,
    },
  ],
});
