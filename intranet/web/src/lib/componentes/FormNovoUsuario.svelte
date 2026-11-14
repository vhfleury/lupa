<script lang="ts">
  import { chamar, mensagemErro } from '$lib/api';
  import type { UsuarioComSenha } from '$lib/tipos';
  import Aviso from './Aviso.svelte';

  interface Props {
    aoCriar: (criado: UsuarioComSenha) => void;
  }

  let { aoCriar }: Props = $props();

  let nome = $state('');
  let erro = $state('');
  let enviando = $state(false);
  const PADRAO_NOME = '[a-z0-9][a-z0-9._\\-]{2,63}';
  const idBase = `novo-${Math.random().toString(36).slice(2, 8)}`;

  async function enviar(evento: SubmitEvent): Promise<void> {
    evento.preventDefault();
    erro = '';
    enviando = true;
    try {
      const criado = await chamar<UsuarioComSenha>('POST', '/usuarios', {
        nome_usuario: nome.trim(),
        papel: 'assessor',
      });
      nome = '';
      aoCriar(criado);
    } catch (e) {
      erro = mensagemErro(e);
    } finally {
      enviando = false;
    }
  }
</script>

<form class="cartao" onsubmit={enviar} aria-labelledby="{idBase}-titulo">
  <h2 id="{idBase}-titulo">Novo assessor</h2>
  {#if erro}<Aviso tipo="erro">{erro}</Aviso>{/if}
  <div class="campo">
    <label for="{idBase}-nome">Nome de usuário</label>
    <input
      id="{idBase}-nome"
      bind:value={nome}
      required
      minlength="3"
      maxlength="64"
      pattern={PADRAO_NOME}
      autocomplete="off"
      aria-describedby="{idBase}-dica"
    />
    <p class="dica" id="{idBase}-dica">
      3 a 64 caracteres: letras minúsculas, números, ponto, hífen ou sublinhado.
    </p>
  </div>
  <button type="submit" disabled={enviando}>Criar assessor</button>
</form>
