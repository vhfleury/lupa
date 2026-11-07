<script lang="ts">
  import '../app.css';
  import type { Snippet } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { configurarManipuladores } from '$lib/api';
  import Cabecalho from '$lib/componentes/Cabecalho.svelte';
  import MenuLateral from '$lib/componentes/MenuLateral.svelte';
  import SeletorTema from '$lib/componentes/SeletorTema.svelte';
  import { consumirMarcador } from '$lib/marcador';
  import { encerrarSessao, sessao } from '$lib/sessao.svelte';
  import { visualizacao, type PerfilVisualizacao } from '$lib/visualizacao.svelte';

  let { children }: { children: Snippet } = $props();

  configurarManipuladores({
    sessaoExpirada: () => {
      consumirMarcador();
      sessao.definir(null);
      void goto('/login?motivo=expirada');
    },
    trocaObrigatoria: () => {
      void goto('/trocar-senha');
    },
  });

  const atual = $derived(sessao.atual);
  const real = $derived(sessao.real);
  async function visualizarPerfil(perfil: PerfilVisualizacao): Promise<void> {
    await goto('/');
    visualizacao.iniciar(sessao.real, perfil);
  }
  const comMoldura = $derived(
    atual !== null && !atual.troca_senha_obrigatoria && page.url.pathname !== '/login',
  );

  async function sair(): Promise<void> {
    await encerrarSessao();
    await goto('/login');
  }
</script>

<!-- 6.10: o roteador do SvelteKit trata o "#conteudo" sem mover o foco; movemos à mão. -->
<a
  class="pular"
  href="#conteudo"
  onclick={(evento) => {
    evento.preventDefault();
    document.getElementById('conteudo')?.focus();
  }}>Pular para o conteúdo</a
>
{#if comMoldura && atual && real}
  <Cabecalho
    sessao={real}
    aoSair={sair}
    aoVisualizarAssessor={() => visualizarPerfil('assessor')}
    aoVisualizarDesembargador={() => visualizarPerfil('desembargador')}
    visualizandoAssessor={visualizacao.ativa}
  />
  {#if visualizacao.ativa}
    <aside class="aviso-visualizacao" aria-label={`Visualização como ${visualizacao.perfil}`}>
      <div>
        <strong>Visualizando como {visualizacao.perfil}</strong>
        <p>
          Prévia dos menus e controles, somente para consulta. Os dados são os acessíveis à sua
          conta, sem simular o gabinete de outro usuário.
        </p>
      </div>
      <button type="button" class="secundario" onclick={() => visualizacao.encerrar()}
        >Voltar ao meu perfil</button
      >
    </aside>
  {/if}
  <div class="corpo">
    <MenuLateral sessao={atual} caminho={page.url.pathname} />
    <main id="conteudo" tabindex="-1">
      <fieldset class="conteudo-pagina" disabled={visualizacao.ativa}>
        {@render children()}
      </fieldset>
    </main>
  </div>
{:else}
  <main
    id="conteudo"
    class="avulso"
    class:pagina-login={page.url.pathname === '/login'}
    tabindex="-1"
  >
    {@render children()}
    <footer class="rodape"><SeletorTema id="tema-avulso" /></footer>
  </main>
{/if}

<style>
  .conteudo-pagina {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  .aviso-visualizacao {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 1rem 1.25rem;
    background: var(--aviso-fundo);
    color: var(--aviso-texto);
  }
  .aviso-visualizacao p {
    margin: 0.25rem 0 0;
    font-size: 0.85rem;
    max-width: 55rem;
  }
  .pular {
    position: absolute;
    left: -999px;
    top: 0;
    background: var(--superficie);
    padding: 0.5rem 1rem;
    z-index: 10;
  }
  .pular:focus {
    left: 0.5rem;
    top: 0.5rem;
  }
  .corpo {
    display: flex;
    min-height: calc(100vh - 3.5rem);
  }
  main {
    flex: 1;
    padding: 1.5rem;
    min-width: 0;
    max-width: none;
  }
  .rodape {
    margin-top: 2rem;
    display: flex;
    justify-content: flex-end;
  }
  .avulso {
    max-width: 30rem;
    margin: 3rem auto;
  }
  .avulso.pagina-login {
    width: 100%;
    max-width: none;
    min-height: 100dvh;
    margin: 0;
    padding: 3.25rem 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  .pagina-login .rodape {
    position: absolute;
    top: 1rem;
    right: 1.25rem;
    margin: 0;
  }
  @media (max-width: 40rem) {
    .corpo {
      flex-direction: column;
    }
  }
</style>
