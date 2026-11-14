"""Verifica o isolamento de rede dentro do contêiner do worker (RF-SEG-04)."""

import errno
import socket


def main() -> int:
    """Confere o serviço interno e exige que o kernel recuse o destino externo."""
    with socket.create_connection(("db", 5432), timeout=3):
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
        cliente.settimeout(3)
        resultado = cliente.connect_ex(("1.1.1.1", 443))
    if resultado not in {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EACCES, errno.EPERM}:
        raise RuntimeError(f"isolamento externo não confirmado (TCP retornou {resultado})")
    print("worker: PostgreSQL acessível e conexão externa bloqueada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
