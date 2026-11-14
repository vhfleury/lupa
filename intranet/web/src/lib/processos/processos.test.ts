import { describe, expect, it } from 'vitest';
import { estiloDestaque, paginaDestino, proximoZoom } from '$lib/visualizador/geometria';
import { digitoVerificador, mascararCnj, problemaCnj } from './cnj';
import { formatarBytes, problemaArquivo } from './envio';
import { motivoQuarentena, textoDoValor, legivel, CLASSES } from './rotulos';

describe('número CNJ', () => {
  it('calcula o dígito pelo módulo 97 como o servidor', () => {
    // 0004321-DD.2025.8.09.0001: mesmo gerador dos testes do backend.
    const digito = digitoVerificador('0004321', '2025', '8', '09', '0001');
    expect(problemaCnj(`0004321-${digito}.2025.8.09.0001`)).toBe('');
    const errado = String((Number(digito) + 1) % 100).padStart(2, '0');
    expect(problemaCnj(`0004321-${errado}.2025.8.09.0001`)).toMatch(/Dígito/);
    expect(problemaCnj('123')).toMatch(/formato/);
  });

  it('aplica a máscara só com algarismos', () => {
    expect(mascararCnj('00043214520258090001')).toBe('0004321-45.2025.8.09.0001');
    expect(mascararCnj('0004321a4')).toBe('0004321-4');
  });
});

describe('envio', () => {
  it('recusa extensão, vazio e tamanho acima do limite antes de enviar', () => {
    expect(problemaArquivo({ name: 'a.docx', size: 10 })).toMatch(/PDF ou ZIP/);
    expect(problemaArquivo({ name: 'a.PDF', size: 0 })).toMatch(/vazio/);
    expect(problemaArquivo({ name: 'a.zip', size: 600 * 1024 * 1024 })).toMatch(/512 MB/);
    expect(problemaArquivo({ name: 'autos.pdf', size: 1 })).toBe('');
  });

  it('formata tamanhos', () => {
    expect(formatarBytes(512)).toBe('512 B');
    expect(formatarBytes(1536)).toBe('1.5 KB');
    expect(formatarBytes(500 * 1024 * 1024)).toBe('500 MB');
  });
});

describe('rótulos', () => {
  it('motivo de quarentena legível, inclusive desconhecido', () => {
    expect(motivoQuarentena('senha')).toMatch(/protegido por senha/);
    expect(motivoQuarentena('novo_motivo')).toMatch(/Novo motivo/);
    expect(motivoQuarentena(null)).toBe('Arquivo recusado.');
  });

  it('RF-VAL-01: rótulos das cinco classes cíveis e valores de fatos', () => {
    expect(Object.keys(CLASSES)).toHaveLength(5);
    expect(legivel('apelacao_civel')).toBe('Apelação cível');
    expect(legivel('peticao_inicial')).toBe('Petição inicial');
    expect(legivel('data_interposicao')).toBe('Data de interposição');
    expect(legivel('data_citacao')).toBe('Data da citação');
    expect(textoDoValor(8)).toBe('8');
    expect(textoDoValor({ nome: 'Ana', oab: 'GO 123' })).toBe('Nome: Ana · OAB: GO 123');
    expect(textoDoValor(false)).toBe('Não');
  });
});

describe('geometria do destaque', () => {
  it('posiciona em porcentagem sem sair da página', () => {
    expect(estiloDestaque({ x: 0.1, y: 0.2, largura: 0.5, altura: 0.05 })).toBe(
      'left:10.000%;top:20.000%;width:50.000%;height:5.000%',
    );
    expect(estiloDestaque({ x: 0.9, y: -1, largura: 0.5, altura: 2 })).toBe(
      'left:90.000%;top:0.000%;width:10.000%;height:100.000%',
    );
  });

  it('zoom e navegação dentro dos limites', () => {
    expect(proximoZoom(1, 1)).toBe(1.25);
    expect(proximoZoom(0.5, -1)).toBe(0.5);
    expect(proximoZoom(3, 1)).toBe(3);
    expect(paginaDestino(1, -1, 10)).toBe(1);
    expect(paginaDestino(10, 1, 10)).toBe(10);
    expect(paginaDestino(4, 1, null)).toBe(5);
  });
});
