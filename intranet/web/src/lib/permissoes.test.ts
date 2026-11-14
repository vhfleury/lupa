import { describe, expect, it } from 'vitest';
import { acoesSobre, gereUsuarios } from './permissoes';
import { ROTULO_PAPEL, type Sessao, type Usuario } from './tipos';

const juiz: Sessao = {
  usuario_id: 'a'.repeat(64),
  nome_usuario: 'desembargador',
  papel: 'desembargador',
  troca_senha_obrigatoria: false,
  permissoes: ['ver_auditoria', 'gerir_assessor', 'resetar_assessor'],
};
const assessor: Usuario = {
  id: 'b'.repeat(64),
  nome_usuario: 'assessor',
  papel: 'assessor',
  ativo: true,
  mfa_confirmado: true,
  troca_senha_obrigatoria: false,
};

describe('RF-ACE-03 e RF-ACE-04 — gestão de assessores', () => {
  it('usa os dois papéis da intranet', () => {
    expect(Object.keys(ROTULO_PAPEL).sort()).toEqual(['assessor', 'desembargador']);
  });
  it('permite ao desembargador gerir assessores sem a seleção de gabinete', () => {
    expect(gereUsuarios(juiz)).toBe(true);
    expect(acoesSobre(juiz, assessor)).toEqual({ gerir: true, resetar: true });
    expect(acoesSobre(juiz, { ...assessor, papel: 'desembargador' })).toEqual({
      gerir: false,
      resetar: false,
    });
    expect(acoesSobre(juiz, { ...assessor, id: juiz.usuario_id })).toEqual({
      gerir: false,
      resetar: false,
    });
  });
  it('assessor não tem acesso à gestão', () => {
    const sessao: Sessao = { ...juiz, papel: 'assessor', permissoes: ['ver_processo', 'anotar'] };
    expect(gereUsuarios(sessao)).toBe(false);
    expect(acoesSobre(sessao, assessor)).toEqual({ gerir: false, resetar: false });
    expect(gereUsuarios(null)).toBe(false);
    expect(acoesSobre(null, assessor)).toEqual({ gerir: false, resetar: false });
  });
});
