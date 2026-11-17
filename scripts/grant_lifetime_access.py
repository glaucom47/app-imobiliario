"""Script administrativo: concede ou atualiza acesso vitalício para uma agência e utilizador no Fecho.

Pode ser executado localmente ou diretamente no shell do PaaS (Railway/Render) onde
a variável DATABASE_URL está configurada.

Exemplos de uso:
    # Simulação (não altera o banco):
    python scripts/grant_lifetime_access.py --email nanandamenegheti@gmail.com

    # Aplicação real:
    python scripts/grant_lifetime_access.py --email nanandamenegheti@gmail.com --agencia "Portugalia Imóveis" --role diretor --confirm
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.user import User  # noqa: E402
from database.connection import SessionLocal  # noqa: E402


def grant_lifetime_access(
    db,
    email: str = None,
    agencia_nome: str = None,
    role: str = "diretor",
    utilizadores: int = 10,
    confirm: bool = False,
) -> dict:
    """Localiza o utilizador e a respetiva agência e aplica o plano vitalício."""
    resultado = {
        "status": "nenhuma_alteracao",
        "tenant_id": None,
        "tenant_nome": None,
        "user_id": None,
        "user_email": None,
        "user_role": None,
        "alteracoes": [],
    }

    user = None
    tenant = None

    if email:
        clean_email = email.strip().lower()
        # Busca exata ou por fragmento seguro
        user = db.query(User).filter(User.email.ilike(f"%{clean_email}%")).first()

    if user and user.tenant:
        tenant = user.tenant
    elif agencia_nome:
        clean_agencia = agencia_nome.strip()
        tenant = db.query(Tenant).filter(Tenant.nome.ilike(f"%{clean_agencia}%")).first()

    if not tenant and not user:
        return resultado

    # Se encontramos tenant mas não o user, procura se há user vinculado
    if tenant and not user and email:
        user = db.query(User).filter(User.agencia_id == tenant.id, User.email.ilike(f"%{email.strip().lower()}%")).first()

    if tenant:
        resultado["tenant_id"] = tenant.id
        resultado["tenant_nome"] = tenant.nome

        if agencia_nome and tenant.nome != agencia_nome.strip():
            resultado["alteracoes"].append(f"Nome da agência: '{tenant.nome}' -> '{agencia_nome.strip()}'")
            if confirm:
                tenant.nome = agencia_nome.strip()

        if tenant.plano_status != "ativo":
            resultado["alteracoes"].append(f"plano_status: '{tenant.plano_status}' -> 'ativo'")
            if confirm:
                tenant.plano_status = "ativo"

        if tenant.trial_termina_em is not None:
            resultado["alteracoes"].append(f"trial_termina_em: '{tenant.trial_termina_em}' -> None (Sem expiração)")
            if confirm:
                tenant.trial_termina_em = None

        if tenant.subscricao_valida_ate is not None:
            resultado["alteracoes"].append("subscricao_valida_ate: removido término")
            if confirm:
                tenant.subscricao_valida_ate = None

        if tenant.plano_periodo != "vitalicio":
            resultado["alteracoes"].append(f"plano_periodo: '{tenant.plano_periodo}' -> 'vitalicio'")
            if confirm:
                tenant.plano_periodo = "vitalicio"

        if (tenant.utilizadores_contratados or 0) < utilizadores:
            resultado["alteracoes"].append(f"utilizadores_contratados: {tenant.utilizadores_contratados} -> {utilizadores}")
            if confirm:
                tenant.utilizadores_contratados = utilizadores

        if not tenant.ativo:
            resultado["alteracoes"].append("tenant.ativo: False -> True")
            if confirm:
                tenant.ativo = True

    if user:
        resultado["user_id"] = user.id
        resultado["user_email"] = user.email
        resultado["user_role"] = user.role

        if not user.ativo:
            resultado["alteracoes"].append(f"user.ativo ({user.email}): False -> True")
            if confirm:
                user.ativo = True

        if role and user.role != role:
            resultado["alteracoes"].append(f"user.role ({user.email}): '{user.role}' -> '{role}'")
            if confirm:
                user.role = role

    if confirm and resultado["alteracoes"]:
        db.commit()
        resultado["status"] = "aplicado"
    elif resultado["alteracoes"]:
        resultado["status"] = "simulado"

    return resultado


def main():
    parser = argparse.ArgumentParser(description="Concede acesso vitalício no Fecho.")
    parser.add_argument("--email", type=str, help="E-mail da conta do utilizador/agência.")
    parser.add_argument("--agencia", type=str, help="Nome da agência a atualizar.")
    parser.add_argument("--role", type=str, default="diretor", choices=["diretor", "consultor"], help="Perfil de acesso (default: diretor).")
    parser.add_argument("--utilizadores", type=int, default=10, help="Quantidade de utilizadores incluídos (default: 10).")
    parser.add_argument("--confirm", action="store_true", help="Efetiva a gravação na base de dados.")

    args = parser.parse_args()

    if not args.email and not args.agencia:
        print("Erro: Forneça pelo menos --email ou --agencia.")
        sys.exit(1)

    db = SessionLocal()
    try:
        res = grant_lifetime_access(
            db=db,
            email=args.email,
            agencia_nome=args.agencia,
            role=args.role,
            utilizadores=args.utilizadores,
            confirm=args.confirm,
        )
    finally:
        db.close()

    if res["status"] == "nenhuma_alteracao":
        print("Nenhum utilizador ou agência localizado com os critérios informados.")
        print(f"Critéros: email={args.email}, agencia={args.agencia}")
        sys.exit(2)

    modo = "CONFIRMADO (GRAVADO)" if res["status"] == "aplicado" else "SIMULAÇÃO (Execute com --confirm para gravar)"
    print(f"\n=== RESULTADO: {modo} ===")
    print(f"Agência: ID {res['tenant_id']} - {res['tenant_nome']}")
    if res['user_email']:
        print(f"Utilizador: ID {res['user_id']} - {res['user_email']} (Role: {res['user_role']})")
    print("\nAlterações identificadas:")
    for alt in res["alteracoes"]:
        print(f" - {alt}")

    if not args.confirm and res["alteracoes"]:
        print("\nPara gravar as alterações na base de dados, execute novamente adicionando o parâmetro --confirm.")


if __name__ == "__main__":
    main()
