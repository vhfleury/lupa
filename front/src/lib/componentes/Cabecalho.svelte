<script lang="ts">
  import SeletorTema from '$lib/componentes/SeletorTema.svelte';
  import { ROTULO_PAPEL, type Sessao } from '$lib/tipos';

  interface Props {
    sessao: Sessao;
    aoSair: () => void;
    aoVisualizarAssessor?: () => void;
    aoVisualizarDesembargador?: () => void;
    visualizandoAssessor?: boolean;
  }

  let { sessao, aoSair, aoVisualizarAssessor, aoVisualizarDesembargador, visualizandoAssessor = false }: Props = $props();
</script>

<header class="cabecalho">
  <a class="marca" href="/">Lupa</a>
  <div class="usuario">
    <SeletorTema id="tema-cabecalho" />
    {#if aoVisualizarDesembargador && !visualizandoAssessor && sessao.papel === 'administrador'}
      <button type="button" class="secundario" onclick={aoVisualizarDesembargador}>Visualizar como desembargador</button>
    {/if}
    {#if aoVisualizarAssessor && !visualizandoAssessor && sessao.papel !== 'assessor'}
      <button type="button" class="secundario" onclick={aoVisualizarAssessor}>Visualizar como assessor</button>
    {/if}
    <span data-testid="usuario-nome">{sessao.nome_usuario}</span>
    <span class="papel" data-testid="usuario-papel">{ROTULO_PAPEL[sessao.papel]}</span>
    <button type="button" class="secundario" onclick={aoSair}>Sair</button>
  </div>
</header>

<style>
  .cabecalho {
    flex-wrap: wrap;
    gap: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 1.25rem;
    background: var(--superficie);
    border-bottom: 1px solid var(--borda);
  }
  .marca {
    font-weight: 700;
    font-size: 1.2rem;
    text-decoration: none;
  }
  .usuario {
    flex-wrap: wrap;
    display: flex;
    gap: 0.75rem;
    align-items: center;
  }
  .papel {
    color: var(--texto-suave);
    border: 1px solid var(--borda);
    border-radius: 999px;
    padding: 0 0.6rem;
    font-size: 0.9rem;
  }
</style>
