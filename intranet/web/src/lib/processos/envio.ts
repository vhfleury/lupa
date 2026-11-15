import { BASE_API, ErroApi } from '$lib/api';
import { visualizacao } from '$lib/visualizacao.svelte';
import type {
  Complemento,
  IdentificacaoIncompleta,
  RespostaEnvio,
  RespostaEnvioProcesso,
} from './tipos';

export const LIMITE_BYTES = 512 * 1024 * 1024;
const EXTENSOES = ['.pdf', '.zip'];

export interface Progresso {
  enviados: number;
  total: number;
}

export interface EnvioEmCurso<T = RespostaEnvio> {
  promessa: Promise<T>;
  cancelar: () => void;
}

/** Problema detectável antes de enviar (o servidor confere de novo pelo conteúdo). */
export function problemaArquivo(arquivo: { name: string; size: number }): string {
  const nome = arquivo.name.toLowerCase();
  if (!EXTENSOES.some((extensao) => nome.endsWith(extensao))) return 'Envie um arquivo PDF ou ZIP.';
  if (arquivo.size === 0) return 'O arquivo está vazio.';
  if (arquivo.size > LIMITE_BYTES) return 'O arquivo passa do limite de 512 MB.';
  return '';
}

export class ErroIdentificacao extends ErroApi {
  constructor(readonly identificacao: IdentificacaoIncompleta) {
    super(422, 'informe os dados que faltam');
  }
}

function erroEnvio(status: number, texto: string): ErroApi {
  try {
    const corpo = JSON.parse(texto);
    if (status === 422 && corpo?.motivo === 'identificacao_incompleta') {
      return new ErroIdentificacao(corpo);
    }
    if (typeof corpo?.detail === 'string') return new ErroApi(status, corpo.detail);
  } catch {
    return new ErroApi(status, 'resposta inválida do servidor');
  }
  return new ErroApi(status, 'não foi possível receber o arquivo');
}

export function enviarArquivo(
  processoId: string,
  arquivo: File,
  aoProgredir: (p: Progresso) => void,
): EnvioEmCurso {
  return enviar(`/processos/${encodeURIComponent(processoId)}/arquivos`, arquivo, {}, aoProgredir);
}

export function enviarProcesso(
  arquivo: File,
  complemento: Complemento,
  aoProgredir: (p: Progresso) => void,
): EnvioEmCurso<RespostaEnvioProcesso> {
  return enviar('/processos/arquivos', arquivo, complemento, aoProgredir);
}

function enviar<T extends RespostaEnvio>(
  rota: string,
  arquivo: File,
  complemento: Complemento,
  aoProgredir: (p: Progresso) => void,
): EnvioEmCurso<T> {
  const xhr = new XMLHttpRequest();
  const query = new URLSearchParams({ nome: arquivo.name, ...complemento });
  const promessa = new Promise<T>((resolver, rejeitar) => {
    if (visualizacao.ativa) {
      rejeitar(new ErroApi(403, 'Encerre a prévia de perfil para realizar alterações.'));
      return;
    }
    xhr.open('POST', `${BASE_API}${rota}?${query}`);
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.upload.onprogress = (evento) => {
      aoProgredir({
        enviados: evento.loaded,
        total: evento.lengthComputable ? evento.total : arquivo.size,
      });
    };
    xhr.upload.onload = () => aoProgredir({ enviados: arquivo.size, total: arquivo.size });
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        rejeitar(erroEnvio(xhr.status, xhr.responseText));
        return;
      }
      try {
        resolver(JSON.parse(xhr.responseText) as T);
      } catch {
        rejeitar(new ErroApi(xhr.status, 'resposta inválida do servidor'));
      }
    };
    xhr.onerror = () => rejeitar(new ErroApi(0, 'falha de rede durante o envio'));
    xhr.onabort = () => rejeitar(new ErroApi(0, 'envio cancelado'));
    xhr.send(arquivo);
  });
  return { promessa, cancelar: () => xhr.abort() };
}

export function formatarBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const unidades = ['KB', 'MB', 'GB'];
  let valor = bytes / 1024;
  let i = 0;
  while (valor >= 1024 && i < unidades.length - 1) {
    valor /= 1024;
    i++;
  }
  return `${valor.toFixed(valor < 10 ? 1 : 0)} ${unidades[i]}`;
}
