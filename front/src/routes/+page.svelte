<script lang="ts">
  import { chamar, mensagemErro } from '$lib/api';
  import Aviso from '$lib/componentes/Aviso.svelte';
  import { sessao, tem } from '$lib/sessao.svelte';
  import { gereUsuarios } from '$lib/permissoes';
  import { visualizacao } from '$lib/visualizacao.svelte';
  import { ROTULO_PAPEL, type Gabinete, type Usuario } from '$lib/tipos';
  import type { ProcessoNaLista } from '$lib/processos/tipos';
  import { SITUACAO, formatarData } from '$lib/processos/rotulos';

  const atual = $derived(sessao.atual);
  const admin = $derived(atual?.papel === 'administrador');
  let processos = $state<ProcessoNaLista[] | null>(null);
  let usuarios = $state<Usuario[] | null>(null);
  let gabinetes = $state<Gabinete[] | null>(null);
  let carregando = $state(true);
  let erros = $state<string[]>([]);
  const pendentes = $derived(processos?.filter(p => ['pendencias', 'falho', 'quarentena'].includes(p.ingestao.situacao)) ?? []);
  const recentes = $derived([...(processos ?? [])].sort((a, b) => b.criado_em.localeCompare(a.criado_em)).slice(0, 5));
  const processando = $derived(processos?.filter(p => p.ingestao.situacao === 'processando').length ?? 0);
  const concluidos = $derived(processos?.filter(p => p.ingestao.situacao === 'concluido').length ?? 0);

  $effect(() => {
    const s = atual;
    if (!s) return;
    let cancelado = false;
    carregando = true;
    processos = null; usuarios = null; gabinetes = null; erros = [];
    const pedidos = [
      { nome: 'Processos', executar: s.papel !== 'administrador' && tem(s, 'ver_processo') ? chamar<ProcessoNaLista[]>('GET', s.papel === 'assessor' ? '/processos?meus=true' : '/processos') : Promise.resolve(null) },
      { nome: 'Usuários', executar: gereUsuarios(s) ? chamar<Usuario[]>('GET', '/usuarios') : Promise.resolve(null) },
      { nome: 'Gabinetes', executar: tem(s, 'gerir_gabinetes') ? chamar<Gabinete[]>('GET', '/gabinetes') : Promise.resolve(null) },
    ];
    void Promise.allSettled(pedidos.map(p => p.executar)).then(resultados => {
      if (cancelado) return;
      const [p, u, g] = resultados;
      if (p?.status === 'fulfilled') processos = p.value as ProcessoNaLista[] | null;
      if (u?.status === 'fulfilled') usuarios = u.value as Usuario[] | null;
      if (g?.status === 'fulfilled') gabinetes = g.value as Gabinete[] | null;
      erros = resultados.flatMap((r, i) => r.status === 'rejected' ? [`${pedidos[i]?.nome}: ${mensagemErro(r.reason)}`] : []);
      carregando = false;
    });
    return () => { cancelado = true; };
  });
</script>

<svelte:head><title>Início · Lupa</title></svelte:head>

{#if atual}
  <div class="painel" aria-busy={carregando}>
    <header class="boas-vindas">
      <div>
        <span class="sobretitulo">LUPA / {ROTULO_PAPEL[atual.papel]}</span>
        <h1>{admin ? 'Estrutura da plataforma' : atual.papel === 'desembargador' ? 'Visão geral do gabinete' : 'Minha área de trabalho'}</h1>
        <p>{admin ? 'Organize gabinetes, responsáveis e permissões de acesso.' : atual.papel === 'desembargador' ? 'Acompanhe a equipe, o acervo e o processamento do gabinete.' : 'Acompanhe seus processos e as próximas atividades.'}</p>
      </div>
      <a class="acao-principal" href={admin ? '/gabinetes' : '/processos'}>{admin ? 'Gerenciar gabinetes' : 'Acessar processos'} <span aria-hidden="true">↗</span></a>
    </header>

    <div class="contexto"><span class="ponto" aria-hidden="true"></span>{visualizacao.ativa ? 'Prévia de perfil · dados da sua conta' : admin ? 'Visão geral · todos os gabinetes' : atual.papel === 'assessor' ? 'Processos sob sua responsabilidade' : 'Visão do seu gabinete'}<span class="contexto-nota">{carregando ? 'Carregando indicadores…' : 'Resumo dos dados disponíveis'}</span></div>
    {#each erros as erro}<Aviso tipo="erro">{erro}</Aviso>{/each}

    {#if admin}
      <section class="indicadores estrutura" aria-label="Estrutura da plataforma">
        <article class="indicador"><span>Gabinetes</span><strong>{gabinetes?.length ?? '—'}</strong><small>Unidades cadastradas</small></article>
        <article class="indicador"><span>Desembargadores</span><strong>{usuarios?.filter(u => u.papel === 'desembargador' && u.ativo).length ?? '—'}</strong><small>Contas ativas</small></article>
        <article class="indicador"><span>Assessores</span><strong>{usuarios?.filter(u => u.papel === 'assessor' && u.ativo).length ?? '—'}</strong><small>Contas ativas</small></article>
        <article class="indicador"><span>Acessos desativados</span><strong>{usuarios?.filter(u => !u.ativo).length ?? '—'}</strong><small>Contas sem acesso ao sistema</small></article>
      </section>
      <div class="colunas">
        <section class="bloco" aria-labelledby="estrutura-titulo"><div class="titulo-bloco"><div><span class="sobretitulo">ORGANIZAÇÃO</span><h2 id="estrutura-titulo">Gabinetes e equipes</h2></div><a href="/gabinetes">Gerenciar →</a></div>
          {#if carregando}<p class="vazio" role="status">Carregando estrutura…</p>
          {:else if gabinetes === null}<p class="nota">Não foi possível carregar os gabinetes.</p>
          {:else if gabinetes.length === 0}<div class="vazio"><strong>Cadastre o primeiro gabinete.</strong><p>Depois, vincule os desembargadores e assessores à unidade.</p><a href="/gabinetes">Cadastrar gabinete →</a></div>
          {:else}<ul class="lista-processos">{#each gabinetes as gabinete (gabinete.id)}<li class="unidade"><strong>{gabinete.nome}</strong><span>{usuarios === null ? 'Equipe indisponível' : usuarios.filter(u => u.gabinete_id === gabinete.id && u.ativo).length + ' usuários ativos'}</span><p class="nota">Desembargadores: {usuarios === null ? 'indisponível' : usuarios.filter(u => u.gabinete_id === gabinete.id && u.papel === 'desembargador' && u.ativo).map(u => u.nome_usuario).join(', ') || 'Nenhum vinculado'}</p></li>{/each}</ul>{/if}
        </section>
        <section class="bloco atalhos" aria-labelledby="admin-acoes"><span class="sobretitulo">ADMINISTRAÇÃO</span><h2 id="admin-acoes">Configuração e acessos</h2>
          <a class="atalho" href="/gabinetes"><div><strong>Estrutura de gabinetes</strong><span>Cadastre unidades e seus desembargadores</span></div><span aria-hidden="true">↗</span></a>
          <a class="atalho" href="/usuarios"><div><strong>Usuários e permissões</strong><span>Gerencie perfis e vínculos com gabinetes</span></div><span aria-hidden="true">↗</span></a>
          <a class="atalho" href="/auditoria"><div><strong>Auditoria de acessos</strong><span>Consulte os registros de atividade</span></div><span aria-hidden="true">↗</span></a>
          <p class="nota">Administrador: estrutura da plataforma.<br />Desembargador: gestão do próprio gabinete.<br />Assessor: análise dos processos.</p>
        </section>
      </div>
    {:else}
    <section class="indicadores" aria-label="Resumo da plataforma">
      <article class="indicador"><span>{atual.papel === 'assessor' ? 'Sob minha responsabilidade' : 'Processos do gabinete'}</span><strong>{processos === null ? '—' : processos.length}</strong><small>{admin ? 'Cadastrados na plataforma' : 'Disponíveis para consulta'}</small></article>
      {#if admin}
        <article class="indicador"><span>Gabinetes</span><strong>{gabinetes === null ? '—' : gabinetes.length}</strong><small>Unidades cadastradas</small></article>
        <article class="indicador"><span>Usuários ativos</span><strong>{usuarios === null ? '—' : usuarios.filter(u => u.ativo).length}</strong><small>Contas habilitadas</small></article>
      {:else}
        <article class="indicador"><span>Em processamento</span><strong>{processos === null ? '—' : processando}</strong><small>Arquivos em preparação</small></article>
        <article class="indicador"><span>Processamento concluído</span><strong>{processos === null ? '—' : concluidos}</strong><small>Consulte os resultados da análise</small></article>
      {/if}
      <article class="indicador atencao"><span>Exigem atenção</span><strong>{processos === null ? '—' : pendentes.length}</strong><small>Pendências, falhas ou quarentena</small></article>
    </section>

    <div class="colunas">
      <section class="bloco" aria-labelledby="recentes-titulo">
        <div class="titulo-bloco"><div><span class="sobretitulo">ACOMPANHAMENTO</span><h2 id="recentes-titulo">{atual.papel === 'assessor' ? 'Meus processos' : 'Processos recentes do gabinete'}</h2></div><a href="/processos">Ver todos <span aria-hidden="true">→</span></a></div>
        {#if carregando}<p class="vazio" role="status">Carregando processos…</p>
        {:else if processos === null}<p class="vazio">Não foi possível carregar os processos. Acesse a lista para tentar novamente.</p>
        {:else if recentes.length === 0}<div class="vazio"><strong>Seu próximo processo começa aqui.</strong><p>Os processos atribuídos a você aparecerão neste painel.</p><a href="/processos">Ir para processos →</a></div>
        {:else}
          <ul class="lista-processos">{#each recentes as processo (processo.id)}<li><a class="linha-processo" href={`/processos/${processo.id}`}><div><strong>{processo.numero_cnj}</strong><span>{processo.classe} · {formatarData(processo.criado_em)}</span></div><span class="situacao" class:pendente={['pendencias', 'falho', 'quarentena'].includes(processo.ingestao.situacao)}>{SITUACAO[processo.ingestao.situacao]}</span></a></li>{/each}</ul>
        {/if}
      </section>

      <section class="bloco atalhos" aria-labelledby="atalhos-titulo"><span class="sobretitulo">SEU ESPAÇO DE TRABALHO</span><h2 id="atalhos-titulo">Acesso rápido</h2>
        <a class="atalho" href="/processos"><div><strong>{admin ? 'Consultar processos' : 'Abrir ou cadastrar processo'}</strong><span>Autos, validações, dossiê e chat</span></div><span aria-hidden="true">↗</span></a>
        {#if admin}<a class="atalho" href="/gabinetes"><div><strong>Gerenciar gabinetes</strong><span>Organize as unidades e os responsáveis</span></div><span aria-hidden="true">↗</span></a>{/if}
        {#if gereUsuarios(atual)}<a class="atalho" href="/usuarios"><div><strong>{admin ? 'Gerenciar usuários' : 'Equipe do gabinete'}</strong><span>{admin ? 'Contas, perfis e acessos' : 'Consulte e gerencie os assessores'}</span></div><span aria-hidden="true">↗</span></a>{/if}
        {#if tem(atual, 'ver_auditoria')}<a class="atalho" href="/auditoria"><div><strong>Consultar auditoria</strong><span>Acompanhe os registros de atividade</span></div><span aria-hidden="true">↗</span></a>{/if}
        {#if atual.papel === 'assessor'}<p class="nota">Para enviar documentos, abra um processo ou cadastre um novo na página de Processos.</p>{/if}
      </section>
    </div>

    {#if atual.papel === 'desembargador'}
      <section class="bloco equipe-gabinete" aria-labelledby="equipe-titulo"><div class="titulo-bloco"><div><span class="sobretitulo">PESSOAS E ACERVO</span><h2 id="equipe-titulo">Equipe do gabinete</h2></div><a href="/usuarios">Gerenciar equipe →</a></div>
        {#if carregando}<p class="nota">Carregando equipe…</p>{:else if usuarios === null}<p class="nota">Equipe indisponível.</p>{:else if usuarios.filter(u => u.papel === 'assessor').length === 0}<p class="nota">Nenhum assessor cadastrado neste gabinete.</p>{:else}<ul class="lista-processos">{#each usuarios.filter(u => u.papel === 'assessor') as usuario (usuario.id)}<li class="unidade"><strong>{usuario.nome_usuario}</strong><span>{usuario.ativo ? 'Ativo' : 'Desativado'}</span></li>{/each}</ul>{/if}
      </section>
    {/if}
    <section class="bloco" aria-labelledby="atencao-titulo"><div class="titulo-bloco"><div><span class="sobretitulo">PRÓXIMOS PASSOS</span><h2 id="atencao-titulo">Pontos de atenção</h2></div><span class="situacao">{processos === null ? '—' : pendentes.length} processos</span></div>
      {#if carregando}<p class="nota">Conferindo o processamento dos arquivos…</p>
      {:else if processos === null}<p class="nota">Indicador indisponível. Consulte os processos para verificar as pendências.</p>
      {:else if pendentes.length === 0}<p class="nota">Nenhuma pendência, falha ou quarentena de processamento identificada nos processos disponíveis.</p>
      {:else}<ul class="lista-processos">{#each pendentes.slice(0, 3) as processo (processo.id)}<li><a class="linha-processo" href={`/processos/${processo.id}`}><div><strong>{processo.numero_cnj}</strong><span>Abra o processo para conferir os arquivos e as pendências.</span></div><span class="situacao pendente">{SITUACAO[processo.ingestao.situacao]}</span></a></li>{/each}</ul>{#if pendentes.length > 3}<a href="/processos">Ver os demais processos →</a>{/if}{/if}
    </section>
    {/if}
    <details class="sessao-detalhes"><summary>Dados da sessão</summary><dl data-testid="estado-sessao"><dt>Usuário</dt><dd>{atual.nome_usuario}</dd><dt>Papel</dt><dd>{ROTULO_PAPEL[atual.papel]}</dd><dt>Gabinete</dt><dd>{atual.gabinete_id ?? 'todos (administração)'}</dd><dt>Situação</dt><dd>Sessão ativa</dd></dl></details>
  </div>
{/if}

<style>
  .equipe-gabinete { margin-bottom: 1.5rem; }
  .painel { width: 100%; max-width: 76rem; margin: 0 auto; }
  .boas-vindas { display: flex; align-items: center; justify-content: space-between; gap: 1.5rem; padding: .5rem 0 1.5rem; }
  .sobretitulo { font-size: .65rem; font-weight: 700; letter-spacing: .13em; color: var(--texto-suave); }
  h1 { font-size: clamp(1.6rem, 3vw, 2.2rem); letter-spacing: -.04em; margin: .55rem 0; overflow-wrap: anywhere; }
  h2 { font-size: 1.1rem; letter-spacing: -.02em; margin: .4rem 0 0; }
  .boas-vindas p, .nota { color: var(--texto-suave); font-size: .9rem; line-height: 1.7; margin: 0; }
  .acao-principal { display: flex; align-items: center; justify-content: center; gap: 1rem; padding: .8rem 1.1rem; border-radius: 10px; background: #063453; color: #fff; text-decoration: none; font-weight: 600; white-space: nowrap; border: 1px solid #22707e; }
  .acao-principal:hover { background: #09516b; }
  .contexto { display: flex; align-items: center; flex-wrap: wrap; gap: .6rem; color: var(--texto-suave); font-size: .8rem; margin: 0 0 1.5rem; }
  .contexto-nota { margin-left: auto; }
  .ponto { width: 7px; height: 7px; border-radius: 50%; background: #008e87; }
  .indicadores { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .indicador, .bloco { background: var(--superficie); border: 1px solid var(--borda); border-radius: 16px; box-shadow: 0 8px 24px rgb(3 30 63 / 5%); }
  .indicador { display: flex; flex-direction: column; padding: 1.25rem; border-top: 3px solid #008e87; }
  .indicador > span { color: var(--texto-suave); font-size: .82rem; }
  .indicador strong { font-size: 2.2rem; font-weight: 600; margin: .25rem 0; letter-spacing: -.04em; }
  .indicador small { color: var(--texto-suave); font-size: .72rem; }
  .indicador.atencao { border-top-color: var(--foco); }
  .colunas { display: grid; grid-template-columns: minmax(0, 2fr) minmax(17rem, 1fr); align-items: start; gap: 1.5rem; margin-bottom: 1.5rem; }
  .unidade { padding: 1rem 0; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .5rem; } .unidade > span { font-size: .8rem; color: var(--texto-suave); } .unidade .nota { grid-column: 1 / -1; overflow-wrap: anywhere; }
  .bloco { padding: 1.5rem; min-width: 0; }
  .titulo-bloco { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.25rem; }
  .titulo-bloco > a { font-size: .8rem; white-space: nowrap; }
  .lista-processos { padding: 0; margin: 0; list-style: none; }
  .lista-processos li + li { border-top: 1px solid var(--borda); }
  .linha-processo { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 0; text-decoration: none; color: var(--texto); }
  .linha-processo div { min-width: 0; }
  .linha-processo strong { font-size: .85rem; overflow-wrap: anywhere; }
  .linha-processo div > span, .atalho div > span { display: block; color: var(--texto-suave); font-size: .75rem; margin-top: .3rem; }
  .situacao { font-size: .7rem; border: 1px solid var(--borda); border-radius: 999px; padding: .25rem .6rem; white-space: nowrap; color: var(--texto-suave); }
  .situacao.pendente { background: var(--aviso-fundo); color: var(--aviso-texto); }
  .atalho { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 0; color: var(--texto); text-decoration: none; border-bottom: 1px solid var(--borda); }
  .atalho strong { font-size: .85rem; }
  .atalho:hover strong, .linha-processo:hover strong { color: var(--primaria); text-decoration: underline; }
  .atalhos .nota { margin-top: 1rem; font-size: .8rem; }
  .vazio { text-align: center; color: var(--texto-suave); padding: 2.5rem 1rem; font-size: .9rem; }
  .vazio strong { color: var(--texto); }
  .sessao-detalhes { margin: 1.5rem 0 .5rem; color: var(--texto-suave); font-size: .8rem; }
  summary { cursor: pointer; }
  dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: .4rem 1rem; } dd { margin: 0; overflow-wrap: anywhere; }
  @media (max-width: 65rem) { .indicadores { grid-template-columns: repeat(2, minmax(0, 1fr)); } .colunas { grid-template-columns: minmax(0, 1fr); } }
  @media (max-width: 40rem) { .boas-vindas { align-items: flex-start; flex-direction: column; padding-top: .5rem; } .contexto { margin-top: .5rem; } .contexto-nota { margin-left: 0; width: 100%; } .bloco { padding: 1rem; } .indicadores { gap: .75rem; } .indicador { padding: 1rem; } .linha-processo { align-items: flex-start; flex-direction: column; gap: .6rem; } }
</style>





