import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { repetirEnquanto } from './repeticao';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('repetirEnquanto', () => {
  it('repete a carga no intervalo enquanto a condição vale e para quando ela deixa de valer', async () => {
    let restantes = 2;
    const carregar = vi.fn(async () => {
      restantes -= 1;
    });
    const repeticao = repetirEnquanto(carregar, () => restantes > 0, 1000);

    await repeticao.executar();
    expect(carregar).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(999);
    expect(carregar).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(carregar).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(5000);
    expect(carregar).toHaveBeenCalledTimes(2);
  });

  it('não agenda mais nada depois de parar', async () => {
    const carregar = vi.fn(async () => {});
    const repeticao = repetirEnquanto(carregar, () => true, 1000);

    await repeticao.executar();
    repeticao.parar();
    await vi.advanceTimersByTimeAsync(5000);

    expect(carregar).toHaveBeenCalledTimes(1);
  });

  it('executar de novo antes do prazo não cria uma segunda repetição', async () => {
    const carregar = vi.fn(async () => {});
    const repeticao = repetirEnquanto(carregar, () => true, 1000);

    await repeticao.executar();
    await repeticao.executar();
    await vi.advanceTimersByTimeAsync(1000);

    expect(carregar).toHaveBeenCalledTimes(3);
    repeticao.parar();
  });

  it('carga que falha ainda agenda a próxima', async () => {
    const carregar = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error('rede'))
      .mockResolvedValue(undefined);
    const repeticao = repetirEnquanto(carregar, () => true, 1000);

    await expect(repeticao.executar()).rejects.toThrow('rede');
    await vi.advanceTimersByTimeAsync(1000);

    expect(carregar).toHaveBeenCalledTimes(2);
    repeticao.parar();
  });
});
