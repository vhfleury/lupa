<script lang="ts">
  import { chamar, mensagemErro } from '$lib/api';
  import Aviso from '$lib/componentes/Aviso.svelte';
  import { sessao, tem } from '$lib/sessao.svelte';
  type Assessor = { id: string; nome_usuario: string; ativo: boolean };
  type Dados = { responsaveis: Assessor[]; disponiveis: Assessor[]; pode_gerir: boolean };
  let { processoId }: { processoId: string } = $props();
  let dados = $state<Dados | null>(null);
  let selecionados = $state<string[]>([]);
  let carregando = $state(false);
  let salvando = $state(false);
  let erro = $state('');
  let aviso = $state('');
  const podeGerir = $derived(dados?.pode_gerir && tem(sessao.atual, 'gerir_assessor'));
  const mudou = $derived(dados !== null && (selecionados.length !== dados.responsaveis.length || dados.responsaveis.some(u => !selecionados.includes(u.id))));
  async function carregar(): Promise<void> {
    carregando = true; erro = '';
    try {
      dados = await chamar<Dados>('GET', `/processos/${processoId}/responsaveis`);
      selecionados = dados.responsaveis.filter(u => u.ativo).map(u => u.id);
    } catch (e) { erro = mensagemErro(e); }
    finally { carregando = false; }
  }
  $effect(() => { void processoId; void carregar(); });
  async function salvar(evento: SubmitEvent): Promise<void> {
    evento.preventDefault();
    if (!dados || !podeGerir || selecionados.length === 0) return;
    erro = ''; aviso = ''; salvando = true;
    try {
      const resultado = await chamar<{ responsaveis: Assessor[] }>('POST', `/processos/${processoId}/responsaveis`, {
        usuarios: selecionados, anteriores: dados.responsaveis.map(u => u.id),
      });
      dados = { ...dados, responsaveis: resultado.responsaveis };
      selecionados = resultado.responsaveis.map(u => u.id);
      aviso = 'Responsáveis atualizados. O processo aparece na área de trabalho de cada assessor selecionado.';
    } catch (e) { erro = mensagemErro(e); }
    finally { salvando = false; }
  }
</script>

<section class="cartao responsaveis" aria-labelledby="titulo-responsaveis">
  <h2 id="titulo-responsaveis">Assessores responsáveis</h2>
  {#if erro}<Aviso tipo="erro">{erro}</Aviso><button type="button" class="secundario" onclick={carregar} disabled={salvando || carregando}>Recarregar responsáveis</button>{/if}
  {#if aviso}<Aviso tipo="sucesso">{aviso}</Aviso>{/if}
  {#if carregando}<p role="status">Carregando responsáveis…</p>
  {:else if dados}
    {#if dados.responsaveis.length === 0}<p class="dica">Nenhum assessor atribuído.</p>
    {:else}<ul class="atuais">{#each dados.responsaveis as usuario (usuario.id)}<li>{usuario.nome_usuario}{#if !usuario.ativo} <span class="dica">(desativado)</span>{/if}</li>{/each}</ul>{/if}
    {#if podeGerir}
      <form onsubmit={salvar}>
        <p class="dica">Selecione um ou mais assessores do gabinete. Para transferir, desmarque o responsável atual e selecione o novo. Mantenha pelo menos um responsável.</p>
        <fieldset disabled={salvando}><legend>Responsáveis pelo processo</legend>
          {#each dados.disponiveis as usuario (usuario.id)}<label class="opcao"><input type="checkbox" value={usuario.id} bind:group={selecionados} />{usuario.nome_usuario}</label>{/each}
          {#if dados.disponiveis.length === 0}<p class="dica">Cadastre ou reative um assessor do gabinete para atribuir este processo.</p>{/if}
        </fieldset>
        <button type="submit" disabled={salvando || selecionados.length === 0 || !mudou}>{salvando ? 'Salvando…' : 'Salvar responsáveis'}</button>
      </form>
    {/if}
  {/if}
</section>
<style>
  .responsaveis { margin: 1.5rem 0; border-radius: 16px; }
  h2 { margin-top: 0; }
  .atuais { display: flex; flex-wrap: wrap; gap: .5rem; padding: 0; list-style: none; }
  .atuais li { border: 1px solid var(--borda); border-radius: 999px; padding: .35rem .75rem; }
  fieldset { border: 1px solid var(--borda); border-radius: 10px; margin: 1rem 0; padding: 1rem; }
  .opcao { display: flex; align-items: center; gap: .65rem; padding: .4rem 0; font-weight: 400; }
  .opcao input { width: 1.1rem; height: 1.1rem; }
</style>
