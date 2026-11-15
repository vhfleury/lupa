import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { sessao } from '$lib/sessao.svelte';
import Processos from '../../routes/processos/+page.svelte';
import Detalhe from '../../routes/processos/[id]/+page.svelte';
import { digitoVerificador } from './cnj';

const id = 'ab'.repeat(32);
const numero = `0004321-${digitoVerificador('0004321', '2025', '8', '09', '0001')}.2025.8.09.0001`;
const arquivo = new File(['sintético'], 'autos & anexos.pdf', { type: 'application/pdf' });

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$app/state', () => ({ page: { params: { id: 'ab'.repeat(32) }, state: {} } }));

function logar() {
  sessao.definir({
    usuario_id: '01'.repeat(32),
    nome_usuario: 'assessora',
    papel: 'assessor',
    troca_senha_obrigatoria: false,
    permissoes: ['subir_processo', 'anotar'],
  });
}

afterEach(() => {
  sessao.definir(null);
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

class EnvioTeste {
  static envios: EnvioTeste[] = [];
  url = '';
  corpo?: File;
  status = 0;
  responseText = '';
  upload = { onload: () => {}, onprogress: vi.fn<(evento: Partial<ProgressEvent>) => void>() };
  onload = () => {};
  abort() {}
  open(_metodo: string, url: string) {
    this.url = url;
  }
  setRequestHeader() {}
  send(corpo: File) {
    this.corpo = corpo;
    EnvioTeste.envios.push(this);
  }
  responder(status: number, json: unknown) {
    this.status = status;
    this.responseText = JSON.stringify(json);
    this.onload();
  }
  static obter(indice: number) {
    const envio = EnvioTeste.envios[indice];
    if (!envio) throw new Error('Envio esperado não ocorreu');
    return envio;
  }
}

async function abrirEnvio() {
  logar();
  EnvioTeste.envios = [];
  vi.stubGlobal('XMLHttpRequest', EnvioTeste);
  vi.stubGlobal('fetch', () => Promise.resolve(Response.json([])));
  render(Processos);
  await fireEvent.click(screen.getByRole('button', { name: /Novo processo/ }));
  return screen.getByLabelText('Arquivo PDF ou ZIP (até 512 MB)');
}

async function iniciarEnvio() {
  await fireEvent.change(await abrirEnvio(), { target: { files: [arquivo] } });
  await fireEvent.click(screen.getByRole('button', { name: 'Enviar' }));
  return EnvioTeste.obter(0);
}

it('RF-PRO-01 identifica o arquivo e reenvia os mesmos bytes com a classe que faltou', async () => {
  const envio = await iniciarEnvio();
  expect(new URL(envio.url, location.origin).pathname).toBe('/api/processos/arquivos');
  expect(new URL(envio.url, location.origin).searchParams.get('nome')).toBe(arquivo.name);
  expect(screen.queryByLabelText('Classe')).toBeNull();
  envio.upload.onprogress({ loaded: 3, total: arquivo.size, lengthComputable: true });
  await waitFor(() => expect(screen.getByRole('progressbar')).toHaveValue(3));
  envio.upload.onload();
  expect(await screen.findByText('Identificando o processo…')).toBeInTheDocument();
  envio.responder(422, {
    motivo: 'identificacao_incompleta',
    detail: 'Informe o que faltou.',
    lido: { numero_cnj: numero, classe: null },
    faltando: ['classe'],
    numeros_encontrados: [numero],
  });
  expect(await screen.findByText(numero)).toBeInTheDocument();
  expect(screen.queryByLabelText('Número CNJ')).toBeNull();
  await fireEvent.change(screen.getByLabelText('Classe'), { target: { value: 'agravo_interno' } });
  await fireEvent.click(screen.getByRole('button', { name: 'Confirmar e reenviar' }));
  const reenvio = EnvioTeste.obter(1);
  expect(reenvio.corpo).toBe(envio.corpo);
  expect(reenvio.corpo).toBe(arquivo);
  expect(Object.fromEntries(new URL(reenvio.url, location.origin).searchParams)).toEqual({
    nome: arquivo.name,
    classe: 'agravo_interno',
  });
  reenvio.responder(201, { processo_id: id, processo_criado: true, duplicado: false });
  await waitFor(() =>
    expect(goto).toHaveBeenCalledWith(`/processos/${id}`, {
      state: { avisoCadastro: 'Processo criado e arquivo recebido.' },
    }),
  );
});

it('RF-PRO-01 permite escolher o CNJ encontrado ou digitar outro e preserva o arquivo em erro', async () => {
  const envio = await iniciarEnvio();
  const outro = `0001234-${digitoVerificador('0001234', '2025', '8', '09', '0001')}.2025.8.09.0001`;
  envio.responder(422, {
    motivo: 'identificacao_incompleta',
    lido: { numero_cnj: null, classe: 'apelacao_civel' },
    faltando: ['numero_cnj'],
    numeros_encontrados: [numero, outro],
  });
  expect(await screen.findByText('Apelação cível')).toBeInTheDocument();
  expect(screen.queryByLabelText('Classe')).toBeNull();
  const reenviar = screen.getByRole('button', { name: 'Confirmar e reenviar' });
  expect(reenviar).toBeDisabled();
  await fireEvent.click(screen.getByRole('button', { name: outro }));
  expect(screen.getByLabelText('Número CNJ')).toHaveValue(outro);
  await fireEvent.click(reenviar);
  const reenvio = EnvioTeste.obter(1);
  expect(new URL(reenvio.url, location.origin).searchParams.get('numero_cnj')).toBe(outro);
  reenvio.responder(422, { motivo: 'senha', detail: 'O arquivo está protegido por senha.' });
  expect(await screen.findByRole('alert')).toHaveTextContent(/protegido por senha/);
  expect(
    screen.getByLabelText<HTMLInputElement>('Arquivo PDF ou ZIP (até 512 MB)').files?.[0],
  ).toBe(arquivo);
});

it('RF-PRO-01 avisa o problema de arquivo antes de iniciar o envio', async () => {
  await fireEvent.change(await abrirEnvio(), { target: { files: [new File([], 'vazio.pdf')] } });
  expect(await screen.findByRole('alert')).toHaveTextContent('O arquivo está vazio.');
  expect(EnvioTeste.envios).toHaveLength(0);
});

it('RF-FAT-04 e RF-PRO-06 exibem partes, dados da capa e histórico após corrigir a classe', async () => {
  logar();
  const processo = { id, numero_cnj: numero, classe: 'apelacao_civel', status: 'ativo' };
  const campos: [string, string, string][] = [
    ['relator', 'Relator', 'Des. Exemplo'],
    ['orgao_julgador', 'Órgão julgador', 'Câmara Exemplo'],
    ['assunto', 'Assunto', 'Exemplo de assunto'],
    ['valor_causa', 'Valor da causa', '1234.56'],
    ['juizo_origem', 'Juízo de origem', 'Vara Exemplo'],
    ['data_distribuicao', 'Data de distribuição', '2025-04-08'],
  ];
  const requisitar = vi.fn(async (url: string, init: RequestInit) => {
    if (url.endsWith('/dossie'))
      return Response.json({
        ficha: {
          partes: [{ id: 'a', nome: 'Ana Exemplo', polo: 'ativo', evidencia_id: 'ef' }],
          dados_capa: campos.map(([tipo, , valor], i) => ({
            tipo,
            valor,
            fato_id: String(i),
            evidencia_id: 'ev' + i,
          })),
        },
      });
    if (url.endsWith('/arquivos')) return Response.json({ arquivos: [], situacao: 'sem_arquivos' });
    if (url.endsWith('/responsaveis'))
      return Response.json({ responsaveis: [], disponiveis: [], pode_gerir: false });
    if (url.endsWith('/classe'))
      return Response.json({
        ...processo,
        ...JSON.parse(String(init.body)),
        classe_anterior: 'apelacao_civel',
        classe_corrigida_por_id: '01'.repeat(32),
        classe_corrigida_em: '2025-04-09T12:00:00Z',
      });
    return Response.json(processo);
  });
  vi.stubGlobal('fetch', requisitar);
  render(Detalhe);
  expect(await screen.findByRole('link', { name: 'Ana Exemplo' })).toHaveAttribute(
    'href',
    `/processos/${id}/visualizador?evidencia=ef`,
  );
  expect(screen.getByText(/Polo ativo/)).toBeInTheDocument();
  for (const [, rotulo] of campos) expect(screen.getByText(rotulo)).toBeInTheDocument();
  expect(screen.getByText('08/04/2025')).toBeInTheDocument();
  expect(screen.getByText(/1\.234,56/)).toBeInTheDocument();
  await fireEvent.click(screen.getByRole('button', { name: 'Corrigir classe' }));
  await fireEvent.change(screen.getByLabelText('Nova classe'), {
    target: { value: 'agravo_interno' },
  });
  await fireEvent.click(screen.getByRole('button', { name: 'Salvar classe' }));
  expect(await screen.findByText('Classe anterior')).toBeInTheDocument();
  expect(screen.getByText('Agravo interno')).toBeInTheDocument();
  expect(screen.getByText('Apelação cível')).toBeInTheDocument();
  expect(screen.getByText('assessora')).toBeInTheDocument();
  expect(screen.getByText(/09\/04\/2025/)).toBeInTheDocument();
});
