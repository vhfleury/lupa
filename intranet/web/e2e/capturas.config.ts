// Os guias mostram um processo cível recém-ingerido. O projeto de acesso prepara o magistrado.
import { defineConfig } from '@playwright/test';
import base from './playwright.config';

const acesso = base.projects?.find((p) => p.name === 'acesso');
if (!acesso) throw new Error('projeto de acesso ausente');

export default defineConfig({
  ...base,
  testDir: '.',
  projects: [
    { ...acesso, testDir: './testes' },
    {
      name: 'capturas',
      testDir: '.',
      testMatch: /capturas\.spec\.ts$/,
      dependencies: ['acesso'],
      use: { ...acesso.use, viewport: { width: 1200, height: 760 } },
    },
  ],
});
