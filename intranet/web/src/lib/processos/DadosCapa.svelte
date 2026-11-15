<script lang="ts">
  import type { Dossie } from './tipos';
  import { formatarData, legivel } from './rotulos';

  let { processoId, dados }: { processoId: string; dados: Dossie['ficha']['dados_capa'] } =
    $props();
  const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  function formatar(tipo: string, valor: string) {
    if (tipo === 'valor_causa' && /^\d+(\.\d+)?$/.test(valor)) {
      return moeda.format(valor as `${number}`);
    }
    if (tipo === 'data_distribuicao') return formatarData(valor);
    return valor;
  }
</script>

{#each dados as dado (dado.fato_id)}
  <dt>{legivel(dado.tipo)}</dt>
  <dd>
    <a href="/processos/{processoId}/visualizador?evidencia={dado.evidencia_id}"
      >{formatar(dado.tipo, dado.valor)}</a
    >
  </dd>
{/each}

<style>
  dt {
    font-weight: 600;
  }
  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
</style>
