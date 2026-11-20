# Arquitetura do Lupa 0.2

O Lupa atende um gabinete cível de segundo grau. O assessor e o desembargador consultam os mesmos autos. O processo é identificado pelo número CNJ e por uma das cinco classes admitidas. Toda conferência liga o resultado à página que sustenta os valores usados.

## Componentes

| Componente | Trabalho | Armazenamento ou conexão |
| --- | --- | --- |
| Caddy | HTTPS, cabeçalhos de segurança e encaminhamento de tudo ao front | `/api` não é exposto: o navegador só fala com o front. |
| Front Django (`lupa_web`) | Renderiza as telas no servidor, com HTMX, e chama a API pela rede interna | Sem banco nem sessão própria; repassa o cookie de sessão e o IP do cliente à API e guarda o envio pendente de complemento no volume `envios-pendentes`. Recebe `LUPA_AMBIENTE`, que só abre a página `/padrao` em `desenvolvimento`. |
| API FastAPI (`lupa_api`) | Autenticação, cadastro, recebimento, dossiê, chat, revisão e auditoria | A API importa o pacote da pipeline e acessa PostgreSQL, MinIO e a API do modelo quando solicitada. |
| Worker Python | Inventário, extração, OCR, saneamento, identificação de peças e fatos e cálculo de achados | A rede de ingestão é interna. O worker consulta o PostgreSQL e usa MinIO dentro da implantação. |
| PostgreSQL | Hubs, vínculos, satélites versionados, fila e cadeia de auditoria | A aplicação usa o papel `lupa_app`. As consultas leem as views e as escritas passam pelas funções de gravação. |
| MinIO | Originais e imagens renderizadas | Os arquivos vão em claro para o bucket interno; a proteção em repouso cabe ao host e aos volumes. |

## Percurso de um arquivo

1. O usuário envia o PDF ou ZIP ao front, que o repassa à API em streaming. Ainda no temporário, a API executa a inspeção e lê a capa em subprocessos com limites, ambiente filtrado e sockets bloqueados. Valida o dígito CNJ e identifica a classe pelo rótulo. Se faltar identificação, o front guarda o arquivo por até 2 horas e o reenvia com o complemento. Uma recusa estrutural encerra a tentativa.
2. Sob trava transacional pelo número CNJ, a API localiza o processo ou o cria. Deduplica pelo SHA-256 dos bytes, grava o original no bucket e registra a recepção e a auditoria. A view da fila passa a apresentar o arquivo.
3. Um worker mantém o lock de sessão na conexão física e consome a fila em ordem de recebimento. O ambiente de parsing limita memória, CPU e tempo do subprocesso. A extração combina texto nativo e OCR conforme a página, guarda evidências e marca conteúdo suspeito.
4. A classificação identifica as peças. Os extratores localizam partes e fatos, inclusive os seis campos da capa, e conferem os offsets contra o texto da página. O catálogo seleciona as regras pela classe e avalia os fatos de cada recorrente. Uma correção de classe preserva o criador e recalcula os achados na mesma transação.
5. No dossiê e no visualizador, a pessoa abre a evidência para conferir a página. Uma correção grava outra versão do fato e recalcula os achados. Uma reexecução respeita a classificação manual e os fatos confirmados ou corrigidos.
6. O chat consulta o processo aberto e verifica as citações da resposta antes de mostrá-las. O registro de auditoria guarda atos, identificadores e metadados de uso. O texto dos autos e das conversas fica nos satélites de conteúdo, fora da auditoria.

## Falhas e recuperação

A queda da conexão libera o lock da fila. A retomada reaproveita as páginas e lotes gravados e registra novas tentativas. A API expõe a saúde de `api`, `db` e `minio` e o worker responde a um healthcheck do PostgreSQL. Um incidente no chat pode colocar o processo em revisão. Só o desembargador libera a consulta ao modelo. Ao descartar, a aplicação apaga os satélites de conteúdo do processo e permite retomar uma limpeza pendente do bucket.

O Compose entregue é de desenvolvimento. Uma perda dos volumes torna os dados irrecuperáveis. Os procedimentos de operação e os campos do relatório de uso estão no [manual de operação](operacao/operacao.md).

## Referências

A [especificação cível](especificacao/0.2/especificacao.md) define os papéis e as cinco classes. O [plano de execução](planos/plano_0.2_execucao.md) descreve os algoritmos e o [índice técnico](README.md) reúne os documentos por componente.
