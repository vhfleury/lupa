<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { chamar, mensagemErro } from '$lib/api';
  import Aviso from '$lib/componentes/Aviso.svelte';
  import NovoProcesso from '$lib/processos/NovoProcesso.svelte';
  import { formatarData, CLASSES, SITUACAO } from '$lib/processos/rotulos';
  import type { ProcessoNaLista } from '$lib/processos/tipos';
  import { repetirEnquanto } from '$lib/repeticao';
  import { sessao, tem } from '$lib/sessao.svelte';

  const INTERVALO_MS = 4000;

  let busca = $state('');
  let situacao = $state('');
  let responsavel = $state('');
  let novoAberto = $state(false);
  let processos = $state<ProcessoNaLista[]>([]);
  let carregando = $state(true);
  let erro = $state('');

  const atual = $derived(sessao.atual);
  const podeCriar = $derived(tem(atual, 'subir_processo'));
  const processando = $derived(processos.some((p) => p.ingestao.situacao === 'processando'));

  const assessores = $derived(
    [
      ...new Map(processos.flatMap((p) => p.responsaveis ?? []).map((u) => [u.id, u])).values(),
    ].sort((a, b) => a.nome_usuario.localeCompare(b.nome_usuario)),
  );
  const filtrados = $derived(
    processos.filter((p) => {
      const texto =
        `${p.numero_cnj} ${CLASSES[p.classe]} ${(p.responsaveis ?? []).map((u) => u.nome_usuario).join(' ')}`.toLocaleLowerCase(
          'pt-BR',
        );
      return (
        (!busca.trim() || texto.includes(busca.trim().toLocaleLowerCase('pt-BR'))) &&
        (!situacao || p.ingestao.situacao === situacao) &&
        (!responsavel ||
          (responsavel === 'sem'
            ? !p.responsaveis?.length
            : p.responsaveis?.some((u) => u.id === responsavel)))
      );
    }),
  );
  async function carregar(): Promise<void> {
    try {
      processos = await chamar<ProcessoNaLista[]>('GET', '/processos');
      erro = '';
    } catch (e) {
      erro = mensagemErro(e);
    } finally {
      carregando = false;
    }
  }

  const atualizacao = repetirEnquanto(carregar, () => processando, INTERVALO_MS);
  onMount(() => void atualizacao.executar());
  onDestroy(atualizacao.parar);
</script>

<svelte:head><title>Processos · Lupa</title></svelte:head>

<div class="pagina-processos">
  <header class="topo">
    <div>
      <span class="sobretitulo">ACERVO / PROCESSOS</span>
      <h1>Processos</h1>
      <p>Consulte os autos, acompanhe o processamento e veja quem está responsável.</p>
    </div>
    {#if podeCriar}<button
        type="button"
        class="novo-botao"
        aria-expanded={novoAberto}
        aria-controls="cadastro-processo"
        onclick={() => (novoAberto = !novoAberto)}
        >{novoAberto ? 'Fechar cadastro' : '+ Novo processo'}</button
      >{/if}
  </header>

  {#if erro}<Aviso tipo="erro">{erro}</Aviso>{/if}

  {#if podeCriar && novoAberto}
    <NovoProcesso />
  {/if}

  <section class="acervo" aria-labelledby="titulo-acervo">
    <div class="cabecalho-lista">
      <div>
        <h2 id="titulo-acervo">Lista de processos</h2>
      </div>
      <span class="contagem" aria-live="polite"
        >{carregando ? 'Carregando…' : `${filtrados.length} de ${processos.length}`}</span
      >
    </div>
    <div class="filtros">
      <div>
        <label for="buscar-processo">Buscar processo ou assessor</label><input
          id="buscar-processo"
          type="search"
          bind:value={busca}
          placeholder="Número CNJ, classe ou nome do assessor"
        />
      </div>
      <div>
        <label for="filtro-situacao">Processamento</label><select
          id="filtro-situacao"
          bind:value={situacao}
          ><option value="">Todas as situações</option
          >{#each Object.entries(SITUACAO) as [valor, rotulo]}<option value={valor}>{rotulo}</option
            >{/each}</select
        >
      </div>
      <div>
        <label for="filtro-responsavel">Responsável</label><select
          id="filtro-responsavel"
          bind:value={responsavel}
          ><option value="">Todos os responsáveis</option><option value="sem"
            >Sem responsável</option
          >{#each assessores as assessor (assessor.id)}<option value={assessor.id}
              >{assessor.nome_usuario}{assessor.ativo ? '' : ' (desativado)'}</option
            >{/each}</select
        >
      </div>
    </div>
    {#if carregando}<p class="vazio" role="status">Carregando processos…</p>
    {:else if erro && processos.length === 0}<div class="vazio">
        <p>Não foi possível carregar a lista.</p>
        <button type="button" class="secundario" onclick={carregar}>Tentar novamente</button>
      </div>
    {:else if processos.length === 0}<div class="vazio">
        <strong>Nenhum processo cadastrado.</strong>
        <p>Os processos e seus responsáveis aparecerão aqui.</p>
      </div>
    {:else if filtrados.length === 0}<div class="vazio">
        <strong>Nenhum processo encontrado.</strong>
        <p>Experimente outros termos ou remova os filtros.</p>
        <button
          type="button"
          class="secundario"
          onclick={() => {
            busca = '';
            situacao = '';
            responsavel = '';
          }}>Limpar filtros</button
        >
      </div>
    {:else}
      <div class="tabela-container">
        <table data-testid="lista-processos">
          <thead
            ><tr
              ><th scope="col">Processo</th><th scope="col">Assessores responsáveis</th><th
                scope="col">Processamento</th
              ><th scope="col">Criado em</th></tr
            ></thead
          ><tbody>
            {#each filtrados as p (p.id)}<tr data-processo={p.id}>
                <td data-rotulo="Processo"
                  ><a class="numero-processo" href="/processos/{p.id}">{p.numero_cnj}</a><span
                    class="descricao">{CLASSES[p.classe]}</span
                  ></td
                >
                <td data-rotulo="Assessores responsáveis"
                  ><div class="responsaveis">
                    {#each p.responsaveis ?? [] as assessor (assessor.id)}<span class="responsavel"
                        >{assessor.nome_usuario}{#if !assessor.ativo}<small>
                            · desativado</small
                          >{/if}</span
                      >{:else}<span class="sem-responsavel">Sem responsável atribuído</span>{/each}
                  </div></td
                >
                <td data-rotulo="Processamento"
                  ><span class="selo {p.ingestao.situacao}" data-testid="situacao"
                    >{SITUACAO[p.ingestao.situacao] ?? p.ingestao.situacao}</span
                  ></td
                >
                <td data-rotulo="Criado em" class="data">{formatarData(p.criado_em)}</td>
              </tr>{/each}
          </tbody>
        </table>
      </div>
    {/if}
    <footer class="rodape-lista">
      <span>Abra um processo para consultar os detalhes e os responsáveis.</span
      >{#if processando}<span aria-live="polite">Atualização automática do processamento</span>{/if}
    </footer>
  </section>
</div>

<style>
  .pagina-processos {
    width: 100%;
    max-width: 76rem;
    margin: 0 auto;
  }
  .topo {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.5rem 0 1.75rem;
  }
  .sobretitulo {
    color: var(--texto-suave);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.13em;
  }
  h1 {
    font-size: 2rem;
    letter-spacing: -0.04em;
    margin: 0.5rem 0;
  }
  .topo p {
    color: var(--texto-suave);
    margin: 0;
    font-size: 0.9rem;
  }
  .novo-botao {
    background: #063453;
    border: 1px solid #22707e;
    color: white;
    border-radius: 10px;
    min-height: 46px;
    padding: 0.6rem 1.1rem;
    white-space: nowrap;
  }
  .acervo {
    background: var(--superficie);
    border: 1px solid var(--borda);
    border-top: 3px solid #008e87;
    border-radius: 16px;
    overflow: hidden;
  }
  .cabecalho-lista {
    padding: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }
  .cabecalho-lista h2 {
    margin: 0.4rem 0 0;
  }
  .contagem {
    color: var(--texto-suave);
    font-size: 0.8rem;
  }
  .filtros {
    display: grid;
    grid-template-columns: minmax(0, 2fr) repeat(2, minmax(0, 1fr));
    gap: 1rem;
    padding: 0 1.5rem 1.5rem;
  }
  .filtros label {
    font-size: 0.78rem;
    color: var(--texto-suave);
    margin-bottom: 0.5rem;
  }
  .filtros input,
  .filtros select {
    border-radius: 9px;
    min-height: 44px;
    font-size: 0.85rem;
  }
  table {
    table-layout: fixed;
  }
  th {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--texto-suave);
    background: var(--fundo);
  }
  th:first-child {
    width: 34%;
  }
  th:nth-child(2) {
    width: 28%;
  }
  th:nth-child(3) {
    width: 19%;
  }
  th,
  td {
    padding: 1.1rem 1.5rem;
    text-align: left;
    vertical-align: middle;
  }
  td {
    overflow-wrap: anywhere;
  }
  .numero-processo {
    font-size: 0.87rem;
    font-weight: 600;
    text-decoration: none;
  }
  .numero-processo:hover {
    text-decoration: underline;
  }
  .descricao {
    display: block;
    font-size: 0.77rem;
    color: var(--texto-suave);
    margin-top: 0.45rem;
  }
  .responsaveis {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .responsavel {
    border: 1px solid var(--borda);
    padding: 0.3rem 0.6rem;
    border-radius: 8px;
    font-size: 0.78rem;
  }
  .responsavel small,
  .sem-responsavel,
  .data {
    color: var(--texto-suave);
    font-size: 0.78rem;
  }
  .vazio {
    padding: 3rem 1.5rem;
    text-align: center;
    color: var(--texto-suave);
  }
  .rodape-lista {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 1rem 1.5rem;
    color: var(--texto-suave);
    font-size: 0.73rem;
  }
  @media (max-width: 75rem) {
    .filtros {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .filtros > div:first-child {
      grid-column: 1 / -1;
    }
    th,
    td {
      padding: 1rem;
    }
  }
  @media (max-width: 55rem) {
    .topo {
      align-items: flex-start;
      flex-direction: column;
    }
    .filtros {
      grid-template-columns: minmax(0, 1fr);
    }
    table,
    tbody,
    tr,
    td {
      display: block;
      width: 100%;
    }
    thead {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip-path: inset(50%);
    }
    tr {
      padding: 0.5rem 1rem;
      border-top: 1px solid var(--borda);
    }
    td {
      padding: 0.65rem 0;
      border: 0;
    }
    td::before {
      content: attr(data-rotulo);
      display: block;
      font-size: 0.68rem;
      color: var(--texto-suave);
      margin-bottom: 0.35rem;
    }
  }
  .selo {
    display: inline-block;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    border: 1px solid var(--borda);
    font-size: 0.85rem;
  }
  .selo.concluido {
    background: var(--sucesso-fundo);
    color: var(--sucesso);
  }
  .selo.quarentena,
  .selo.falho {
    background: var(--perigo-fundo);
    color: var(--perigo);
  }
  .selo.processando,
  .selo.pendencias {
    background: var(--aviso-fundo);
    color: var(--aviso-texto);
  }
</style>
