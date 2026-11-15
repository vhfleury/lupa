<script lang="ts">
  import { chamar, mensagemErro } from '$lib/api';
  import Aviso from '$lib/componentes/Aviso.svelte';
  import { sessao, tem } from '$lib/sessao.svelte';
  import DadosCapa from './DadosCapa.svelte';
  import { CLASSES, formatarData, legivel } from './rotulos';
  import type { ClasseProcessual, Dossie, Processo } from './tipos';

  let {
    processo,
    ficha,
    aoCorrigir,
  }: {
    processo: Processo;
    ficha: Dossie['ficha'] | null;
    aoCorrigir: (p: Processo) => void;
  } = $props();
  let editando = $state(false);
  let classe = $state<ClasseProcessual>('apelacao_civel');
  let salvando = $state(false);
  let erro = $state('');
  const podeCorrigir = $derived(tem(sessao.atual, 'anotar') && processo.status !== 'descartado');
  const autor = $derived(
    processo.classe_corrigida_por_id === sessao.atual?.usuario_id
      ? sessao.atual?.nome_usuario
      : (ficha?.responsaveis?.find((r) => r.id === processo.classe_corrigida_por_id)
          ?.nome_usuario ?? processo.classe_corrigida_por_id),
  );

  async function corrigir(evento: SubmitEvent) {
    evento.preventDefault();
    if (salvando || classe === processo.classe || !podeCorrigir) return;
    salvando = true;
    erro = '';
    try {
      const atualizado = await chamar<Processo>('POST', `/processos/${processo.id}/classe`, {
        classe,
      });
      aoCorrigir(atualizado);
      editando = false;
    } catch (e) {
      erro = mensagemErro(e);
    } finally {
      salvando = false;
    }
  }
</script>

<header>
  <h1 class="mono">{processo.numero_cnj}</h1>
  <div class="classe">
    <span>{CLASSES[processo.classe]}</span>
    <span class="dica">{legivel(processo.status)}</span>
    {#if podeCorrigir && !editando}
      <button
        type="button"
        class="secundario"
        onclick={() => {
          classe = processo.classe;
          erro = '';
          editando = true;
        }}>Corrigir classe</button
      >
    {/if}
  </div>
  {#if editando && podeCorrigir}
    <form onsubmit={corrigir}>
      <div class="campo">
        <label for="nova-classe">Nova classe</label>
        <select id="nova-classe" bind:value={classe} disabled={salvando}>
          {#each Object.entries(CLASSES) as [valor, rotulo]}<option value={valor}>{rotulo}</option
            >{/each}
        </select>
      </div>
      {#if erro}<Aviso tipo="erro">{erro}</Aviso>{/if}
      <div class="acoes">
        <button type="submit" disabled={salvando || classe === processo.classe}
          >{salvando ? 'Salvando…' : 'Salvar classe'}</button
        >
        <button
          type="button"
          class="secundario"
          disabled={salvando}
          onclick={() => (editando = false)}>Cancelar</button
        >
      </div>
    </form>
  {/if}

  {#if processo.classe_anterior}
    <dl aria-label="Última correção de classe">
      <dt>Classe anterior</dt>
      <dd>{CLASSES[processo.classe_anterior]}</dd>
      <dt>Corrigida por</dt>
      <dd>{autor}</dd>
      <dt>Corrigida em</dt>
      <dd>{formatarData(processo.classe_corrigida_em)}</dd>
    </dl>
  {/if}
  {#if ficha && (ficha.partes.length || ficha.dados_capa.length)}
    <dl aria-label="Dados dos autos">
      {#if ficha.partes.length}
        <dt>Partes</dt>
        <dd>
          {#each ficha.partes as parte (parte.id)}
            <div>
              <a href="/processos/{processo.id}/visualizador?evidencia={parte.evidencia_id}"
                >{parte.nome}</a
              >
              · Polo {parte.polo}
            </div>
          {/each}
        </dd>
      {/if}
      <DadosCapa processoId={processo.id} dados={ficha.dados_capa} />
    </dl>
  {/if}
</header>

<style>
  header {
    margin-bottom: 1rem;
  }
  .classe {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
  }
  form {
    margin: 1rem 0;
    max-width: 30rem;
  }
  dl {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: 0.4rem 1rem;
  }
  dt {
    font-weight: 600;
  }
  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
</style>
