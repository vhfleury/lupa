// Alternância manual de tema (6.10): claro, escuro ou o do sistema. A escolha fica só no
// localStorage deste navegador (nada vai ao servidor); /inicio.js a aplica antes do primeiro
// desenho e este módulo a troca em tempo de execução.
import { armazenamentoDoNavegador, gravarItem, lerItem } from './armazenamento';

export type Tema = 'claro' | 'escuro' | 'sistema';

export const CHAVE_TEMA = 'lupa.tema';
export const TEMAS: readonly { valor: Tema; rotulo: string }[] = [
  { valor: 'sistema', rotulo: 'Do sistema' },
  { valor: 'claro', rotulo: 'Claro' },
  { valor: 'escuro', rotulo: 'Escuro' },
];

export function lerTema(
  armazenamento: Storage | null = armazenamentoDoNavegador('localStorage'),
): Tema {
  const valor = lerItem(armazenamento, CHAVE_TEMA);
  return valor === 'claro' || valor === 'escuro' || valor === 'sistema' ? valor : 'escuro';
}

export function aplicarTema(tema: Tema, raiz: HTMLElement = document.documentElement): void {
  if (tema === 'sistema') delete raiz.dataset['tema'];
  else raiz.dataset['tema'] = tema;
}

export function escolherTema(
  tema: Tema,
  armazenamento: Storage | null = armazenamentoDoNavegador('localStorage'),
  raiz: HTMLElement = document.documentElement,
): void {
  aplicarTema(tema, raiz);
  gravarItem(armazenamento, CHAVE_TEMA, tema);
}
