# Interface da intranet

A aplicação SvelteKit em `intranet/web/` é servida pelo Caddy sob HTTPS. As chamadas para `/api` usam a mesma origem e a sessão autenticada. O proxy acrescenta os cabeçalhos de segurança e as rotas protegidas validam a sessão e a permissão novamente na API.

Os dois papéis podem cadastrar um processo. Em **Novo processo**, a pessoa envia um PDF ou ZIP. A tela exibe o progresso e aguarda a identificação da capa. Se faltar número ou classe, oferece os números encontrados e solicita os campos necessários. O reenvio reutiliza o arquivo selecionado. A tela do processo informa se houve criação, anexo ou duplicidade.

O cabeçalho consulta o dossiê para mostrar partes, polos e dados da capa com suas fontes. **Corrigir classe** registra a alteração e recalcula os achados. O processo dá acesso aos arquivos, responsáveis, dossiê, índice de peças, histórico de fatos e achados e chat. A evidência abre a página do arquivo com a localização disponível.

A gestão de assessores e a auditoria ficam no menu do desembargador. Quem administra o acervo pode distribuir responsáveis, restabelecer acesso e revisar intercorrências. Os testes de componentes usam Vitest, e os fluxos pela interface, acessibilidade e capturas usam Playwright. [Guia de contribuição](../../CONTRIBUTING.md).

