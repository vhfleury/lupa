// Atualização automática das telas que acompanham a fila de ingestão: recarrega a cada intervalo
// enquanto ainda há algo em andamento e para de vez quando a tela sai.

export interface Repeticao {
  /** Carrega agora e, se a condição valer, agenda a próxima carga (substitui a já agendada). */
  executar: () => Promise<void>;
  /** Cancela a carga agendada e impede novas. */
  parar: () => void;
}

export function repetirEnquanto(
  carregar: () => Promise<void>,
  continuar: () => boolean,
  intervaloMs: number,
): Repeticao {
  let temporizador: ReturnType<typeof setTimeout> | undefined;
  let parado = false;

  async function executar(): Promise<void> {
    clearTimeout(temporizador);
    try {
      await carregar();
    } finally {
      if (!parado && continuar()) temporizador = setTimeout(() => void executar(), intervaloMs);
    }
  }

  function parar(): void {
    parado = true;
    clearTimeout(temporizador);
  }

  return { executar, parar };
}
