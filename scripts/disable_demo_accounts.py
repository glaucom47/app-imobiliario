"""Script administrativo: desativa as contas de demonstração na base de dados.

Contas visadas: consultor@fecho.pt e diretor@fecho.pt.
Ação: marca ativo=False e substitui o hash da palavra-passe por um hash Bcrypt
de um segredo aleatório descartado (as credenciais públicas deixam de funcionar).
Tokens JWT já emitidos são recusados porque app/dependencies.py valida user.ativo.

Por omissão corre em modo de simulação (não altera nada). Para aplicar:
    python scripts/disable_demo_accounts.py --confirm

Em produção, execute na shell do PaaS (Render/Railway), onde DATABASE_URL já está definida.
Nunca regista palavras-passe nem tokens.
"""
import argparse
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt  # noqa: E402

DEMO_EMAILS = ("consultor@fecho.pt", "diretor@fecho.pt")


def disable_demo_accounts(db, confirm: bool = False) -> list[str]:
    """Desativa as contas demo. Devolve a lista de emails afetados (ou a afetar)."""
    from app.models.user import User

    users = db.query(User).filter(User.email.in_(DEMO_EMAILS)).all()
    afetados = []
    for user in users:
        afetados.append(user.email)
        if confirm:
            user.ativo = False
            user.password_hash = bcrypt.hashpw(
                secrets.token_urlsafe(48).encode("utf-8"), bcrypt.gensalt(rounds=12)
            ).decode("utf-8")
    if confirm:
        db.commit()
    return afetados


def main() -> int:
    parser = argparse.ArgumentParser(description="Desativa as contas demo do Fecho.")
    parser.add_argument("--confirm", action="store_true", help="Aplica as alterações (sem isto, apenas simula).")
    args = parser.parse_args()

    from database.connection import SessionLocal

    db = SessionLocal()
    try:
        afetados = disable_demo_accounts(db, confirm=args.confirm)
    finally:
        db.close()

    if not afetados:
        print("Nenhuma conta demo encontrada. Nada a fazer.")
    elif args.confirm:
        print(f"Contas demo desativadas: {', '.join(afetados)}")
    else:
        print(f"[SIMULAÇÃO] Seriam desativadas: {', '.join(afetados)}. Repita com --confirm para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
