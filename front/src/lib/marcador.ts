// Marcador de "havia sessão neste separador" (6.10), só em sessionStorage e sem nenhum dado da
// sessão: serve para, numa recarga completa sem sessão válida, dizer "sessão encerrada ou
// expirada" em vez de mostrar o login como se fosse a primeira vez. Sair apaga o marcador.
import { armazenamentoDoNavegador, gravarItem, lerItem, removerItem } from './armazenamento';

export const CHAVE_MARCADOR = 'lupa.sessao-anterior';

export function marcarSessao(
  armazenamento: Storage | null = armazenamentoDoNavegador('sessionStorage'),
): void {
  gravarItem(armazenamento, CHAVE_MARCADOR, '1');
}

/** Devolve se havia marcador e o apaga (a mensagem aparece uma vez). */
export function consumirMarcador(
  armazenamento: Storage | null = armazenamentoDoNavegador('sessionStorage'),
): boolean {
  const havia = lerItem(armazenamento, CHAVE_MARCADOR) === '1';
  removerItem(armazenamento, CHAVE_MARCADOR);
  return havia;
}
