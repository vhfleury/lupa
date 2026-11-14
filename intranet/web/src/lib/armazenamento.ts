// Acesso ao localStorage e ao sessionStorage que nunca lança. Em modo privado, com cota cheia ou
// com o armazenamento bloqueado, a leitura devolve null e a escrita simplesmente não acontece.
export type TipoArmazenamento = 'localStorage' | 'sessionStorage';

export function armazenamentoDoNavegador(tipo: TipoArmazenamento): Storage | null {
  try {
    return typeof globalThis[tipo] === 'undefined' ? null : globalThis[tipo];
  } catch {
    return null;
  }
}

export function lerItem(armazenamento: Storage | null, chave: string): string | null {
  try {
    return armazenamento?.getItem(chave) ?? null;
  } catch {
    return null;
  }
}

export function gravarItem(armazenamento: Storage | null, chave: string, valor: string): void {
  try {
    armazenamento?.setItem(chave, valor);
  } catch {
    // Sem armazenamento: o valor vale só até recarregar.
  }
}

export function removerItem(armazenamento: Storage | null, chave: string): void {
  try {
    armazenamento?.removeItem(chave);
  } catch {
    // Sem armazenamento: não há o que remover.
  }
}
