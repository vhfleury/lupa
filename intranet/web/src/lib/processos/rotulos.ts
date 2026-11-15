import type { ClasseProcessual } from './tipos';

export const CLASSES: Record<ClasseProcessual, string> = {
  apelacao_civel: 'Apelação cível',
  agravo_instrumento: 'Agravo de instrumento',
  embargos_declaracao: 'Embargos de declaração',
  agravo_interno: 'Agravo interno',
  acao_originaria: 'Ação originária',
};

const ROTULOS: Record<string, string> = {
  ...CLASSES,
  peticao_inicial: 'Petição inicial',
  contestacao: 'Contestação',
  replica: 'Réplica',
  decisao_interlocutoria: 'Decisão interlocutória',
  sentenca: 'Sentença',
  apelacao: 'Apelação',
  contrarrazoes: 'Contrarrazões',
  acordao: 'Acórdão',
  certidao: 'Certidão',
  procuracao: 'Procuração',
  comprovante_preparo: 'Comprovante de preparo',
  laudo_pericial: 'Laudo pericial',
  parecer_mp: 'Parecer do Ministério Público',
  juizo: 'Juízo',
  mp: 'Ministério Público',
  ministerio_publico: 'Ministério Público',
  fazenda_publica: 'Fazenda Pública',
  defensoria_publica: 'Defensoria Pública',
  tempestividade_recurso: 'Tempestividade do recurso',
  preparo_recurso: 'Preparo do recurso',
  representacao_recurso: 'Representação do recorrente',
  cabimento_agravo: 'Cabimento do agravo',
  data_decisao_recorrida: 'Data da decisão recorrida',
  data_intimacao: 'Data da intimação',
  data_interposicao: 'Data de interposição',
  data_comprovante: 'Data do comprovante',
  data_ajuizamento: 'Data do ajuizamento',
  data_citacao: 'Data da citação',
  data_contestacao: 'Data da contestação',
  data_acordao: 'Data do acórdão',
  relator: 'Relator',
  orgao_julgador: 'Órgão julgador',
  assunto: 'Assunto',
  valor_causa: 'Valor da causa',
  juizo_origem: 'Juízo de origem',
  data_distribuicao: 'Data de distribuição',
  tipo_recurso: 'Tipo de recurso',
  qualidade_recorrente: 'Qualidade do recorrente',
  gratuidade_pedido: 'Pedido de gratuidade',
  gratuidade_decisao: 'Decisão sobre a gratuidade',
  advogado_subscritor: 'Advogado subscritor',
  hipotese_decisao_agravada: 'Hipótese da decisão agravada',
  prazo_dias: 'Prazo em dias úteis',
  atraso_dias_uteis: 'Atraso em dias úteis',
  dias_nao_contados: 'Dias não contados',
  versoes_dados: 'Versões dos dados',
  versao_dados: 'Versão dos dados',
  pecas_procuradas: 'Peças consultadas',
  paginas_mandato: 'Folhas do mandato',
  oab: 'OAB',
};

export const ESTADO_JOB: Record<string, string> = {
  recebido: 'Na fila',
  validado: 'Validado',
  em_extracao: 'Extraindo páginas',
  parcial: 'Parcial',
  em_revisao: 'Concluído com pendências',
  concluido: 'Concluído',
  falho: 'Falhou',
  quarentena: 'Em quarentena',
};

export const SITUACAO: Record<string, string> = {
  sem_arquivos: 'Sem arquivos',
  processando: 'Processando',
  quarentena: 'Em quarentena',
  falho: 'Falhou',
  pendencias: 'Com pendências',
  concluido: 'Concluído',
};

export const MOTIVO_QUARENTENA: Record<string, string> = {
  corrompido: 'O arquivo está corrompido e não pôde ser aberto.',
  senha: 'O arquivo está protegido por senha. Envie uma versão sem senha.',
  truncado: 'O PDF está incompleto (o envio ou a cópia foi interrompido).',
  assinatura_invalida: 'A assinatura digital não cobre o documento inteiro.',
  tipo_invalido: 'O conteúdo não é PDF (ou o ZIP tem arquivo que não é PDF).',
  zip_malicioso: 'O ZIP foi recusado por segurança (caminho perigoso, link ou tamanho excessivo).',
};

export const MOTIVO_FALHA: Record<string, string> = {
  limite_memoria: 'O processamento passou do limite de memória.',
  limite_cpu: 'O processamento passou do limite de tempo de CPU.',
  tempo_esgotado: 'O processamento demorou demais.',
  erro_parser: 'Erro ao ler o PDF.',
  arquivo_ausente: 'O arquivo não foi encontrado no armazenamento.',
  erro_interno: 'Erro interno no processamento.',
};

export const RESULTADO: Record<string, string> = {
  conforme: 'Conforme',
  atencao: 'Atenção',
  verificar: 'Verificar',
};

export const STATUS_FATO: Record<string, string> = {
  automatico: 'Automático',
  confirmado: 'Confirmado',
  corrigido: 'Corrigido',
};

export const ESTADOS_FINAIS = new Set([
  'concluido',
  'falho',
  'quarentena',
  'em_revisao',
  'parcial',
]);

/** Texto legível de um identificador em snake_case (`tempestividade_recurso`). */
export function legivel(chave: string): string {
  if (ROTULOS[chave]) return ROTULOS[chave];
  const texto = chave.replace(/_/g, ' ');
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export function motivoQuarentena(motivo: string | null): string {
  if (!motivo) return 'Arquivo recusado.';
  return MOTIVO_QUARENTENA[motivo] ?? `Arquivo recusado (${legivel(motivo)}).`;
}

export function motivoFalha(motivo: string | null): string {
  if (!motivo) return 'Falha no processamento.';
  return MOTIVO_FALHA[motivo] ?? `Falha no processamento (${legivel(motivo)}).`;
}

export function formatarData(iso: string | null): string {
  if (!iso) return '—';
  const so = /^\d{4}-\d{2}-\d{2}$/.test(iso);
  const data = new Date(so ? `${iso}T12:00:00` : iso);
  if (Number.isNaN(data.getTime())) return iso;
  return so
    ? data.toLocaleDateString('pt-BR')
    : data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

export function textoDoValor(v: unknown): string {
  if (v == null) return '—';
  if (typeof v === 'boolean') return v ? 'Sim' : 'Não';
  if (typeof v === 'string') {
    if (DATA_ISO.test(v)) return formatarData(v);
    if (/^[0-9a-f]{64}$/.test(v)) return v.slice(0, 8) + '…';
    return ROTULOS[v] ?? v;
  }
  if (Array.isArray(v)) return v.map(textoDoValor).join(' · ');
  if (typeof v === 'object')
    return Object.entries(v)
      .map(([chave, valor]) => `${legivel(chave)}: ${textoDoValor(valor)}`)
      .join(' · ');
  return String(v);
}

export const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;
