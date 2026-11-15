<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { goto } from '$app/navigation';
  import { ErroApi, mensagemErro } from '$lib/api';
  import Aviso from '$lib/componentes/Aviso.svelte';
  import { mascararCnj, problemaCnj } from './cnj';
  import {
    enviarProcesso,
    ErroIdentificacao,
    problemaArquivo,
    type EnvioEmCurso,
    type Progresso,
  } from './envio';
  import { CLASSES } from './rotulos';
  import type { ClasseProcessual, Complemento, IdentificacaoIncompleta } from './tipos';

  let arquivo = $state<File | null>(null);
  let incompleta = $state<IdentificacaoIncompleta | null>(null);
  let numero = $state('');
  let classe = $state<ClasseProcessual | ''>('');
  let erro = $state('');
  let progresso = $state<Progresso | null>(null);
  let complementoTitulo = $state<HTMLHeadingElement>();
  let envio: EnvioEmCurso | null = null;
  let complemento: Complemento = {};
  const faltaNumero = $derived(incompleta?.faltando.includes('numero_cnj'));
  const faltaClasse = $derived(incompleta?.faltando.includes('classe'));
  const problemaNumero = $derived(faltaNumero ? problemaCnj(numero) : '');
  const permitido = $derived(
    arquivo && !problemaArquivo(arquivo) && !problemaNumero && (!faltaClasse || classe),
  );
  const identificando = $derived(progresso && progresso.enviados >= progresso.total);

  function selecionar(novo: File | null) {
    arquivo = novo;
    erro = novo ? problemaArquivo(novo) : '';
    numero = '';
    classe = '';
    incompleta = null;
    complemento = {};
  }

  onDestroy(() => envio?.cancelar());

  async function enviar(evento: SubmitEvent) {
    evento.preventDefault();
    if (!arquivo || !permitido || envio) return;
    erro = '';
    progresso = { enviados: 0, total: arquivo.size };
    if (faltaNumero) complemento.numero_cnj = numero;
    if (faltaClasse && classe) complemento.classe = classe;
    const atual = enviarProcesso(arquivo, complemento, (p) => (progresso = p));
    envio = atual;
    try {
      const resultado = await atual.promessa;
      const avisoCadastro = resultado.duplicado
        ? 'Este arquivo já foi enviado ao processo.'
        : resultado.processo_criado
          ? 'Processo criado e arquivo recebido.'
          : 'Arquivo anexado ao processo existente.';
      await goto(`/processos/${resultado.processo_id}`, { state: { avisoCadastro } });
    } catch (e) {
      if (e instanceof ErroIdentificacao) {
        progresso = null;
        incompleta = e.identificacao;
        await tick();
        complementoTitulo?.focus();
      } else {
        erro = e instanceof ErroApi && e.detalhe ? e.detalhe : mensagemErro(e);
      }
    } finally {
      envio = null;
      progresso = null;
    }
  }
</script>

<section id="cadastro-processo" class="cartao" aria-labelledby="titulo-novo">
  <h2 id="titulo-novo">Novo processo</h2>
  <form onsubmit={enviar}>
    <div class="campo">
      <label for="novos-autos">Arquivo PDF ou ZIP (até 512 MB)</label>
      <input
        id="novos-autos"
        type="file"
        accept=".pdf,.zip,application/pdf,application/zip"
        disabled={!!progresso}
        onchange={(e) => selecionar(e.currentTarget.files?.[0] ?? null)}
      />
    </div>

    {#if incompleta}
      <h3 bind:this={complementoTitulo} tabindex="-1">Complete a identificação do processo</h3>
      {#if incompleta.lido.numero_cnj}<p>
          Número lido: <strong>{incompleta.lido.numero_cnj}</strong>
        </p>{/if}
      {#if incompleta.lido.classe}<p>
          Classe lida: <strong>{CLASSES[incompleta.lido.classe]}</strong>
        </p>{/if}
      {#if faltaNumero}
        {#if incompleta.numeros_encontrados.length}
          <p class="dica" id="escolha-numero">
            Escolha um dos números encontrados ou digite o número CNJ.
          </p>
          <div class="acoes candidatos" role="group" aria-labelledby="escolha-numero">
            {#each incompleta.numeros_encontrados as candidato (candidato)}
              <button
                type="button"
                class="secundario mono"
                disabled={!!progresso}
                onclick={() => (numero = mascararCnj(candidato))}>{candidato}</button
              >
            {/each}
          </div>
        {/if}
        <div class="campo">
          <label for="cnj">Número CNJ</label>
          <input
            id="cnj"
            inputmode="numeric"
            autocomplete="off"
            placeholder="0000000-00.0000.0.00.0000"
            value={numero}
            oninput={(e) => (numero = mascararCnj(e.currentTarget.value))}
            aria-invalid={!!numero && !!problemaNumero}
            aria-describedby={numero && problemaNumero ? 'cnj-erro' : undefined}
            disabled={!!progresso}
            required
          />
          {#if numero && problemaNumero}<p id="cnj-erro" class="dica">{problemaNumero}</p>{/if}
        </div>
      {/if}
      {#if faltaClasse}
        <div class="campo">
          <label for="classe">Classe</label>
          <select id="classe" bind:value={classe} disabled={!!progresso} required>
            <option value="" disabled>Selecione a classe</option>
            {#each Object.entries(CLASSES) as [valor, rotulo]}<option value={valor}>{rotulo}</option
              >{/each}
          </select>
        </div>
      {/if}
    {/if}
    {#if erro}<Aviso tipo="erro">{erro}</Aviso>{/if}
    {#if progresso}
      <div class="andamento">
        {#if identificando}<span role="status">Identificando o processo…</span>
        {:else}
          {@const percentual = Math.floor((100 * progresso.enviados) / progresso.total)}
          <label for="progresso-cadastro">Enviando… {percentual}%</label>
          <progress id="progresso-cadastro" max={progresso.total} value={progresso.enviados}
            >{percentual}%</progress
          >
          <span class="visualmente-oculto" aria-live="polite"
            >Enviando: {Math.floor(percentual / 10) * 10}%</span
          >
        {/if}
      </div>
    {:else}
      <button type="submit" disabled={!permitido}
        >{incompleta ? 'Confirmar e reenviar' : 'Enviar'}</button
      >
    {/if}
  </form>
</section>

<style>
  section {
    border-radius: 16px;
    margin-bottom: 1.5rem;
  }
  h2 {
    margin-top: 0;
  }
  .campo {
    max-width: 36rem;
  }
  .candidatos {
    margin-bottom: 1rem;
  }
  .andamento {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
  }
</style>
