# Interface da intranet

A aplicação SvelteKit em `intranet/web/` é servida pelo Caddy sob HTTPS. As chamadas para `/api` usam a mesma origem e a sessão autenticada. O proxy acrescenta os cabeçalhos de segurança e as rotas protegidas validam a sessão e a permissão novamente na API.

O menu oferece processos aos dois papéis. A tela de cadastro exige número CNJ e classe processual. Dentro de um processo, a pessoa acessa os arquivos, responsáveis, dossiê, índice de peças, fatos e achados e chat. A evidência abre a página do arquivo com a localização disponível. Fatos e resultados anteriores podem ser consultados no histórico.

A gestão de assessores e a auditoria ficam no menu do desembargador. Quem administra o acervo pode distribuir responsáveis, restabelecer acesso e revisar intercorrências. Os testes de componentes usam Vitest, e os fluxos pela interface, acessibilidade e capturas usam Playwright. [Guia de contribuição](../../CONTRIBUTING.md).

