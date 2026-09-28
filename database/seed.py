"""
Script de Seed para carga inicial de dados no ambiente de desenvolvimento.
Cria:
1. Agência de demonstração (Tenant)
2. Parametrizações padrão da agência (Settings)
3. Catálogo corporativo de tags de objeção (ObjectionTag)
4. Usuários de demonstração (Diretora e Consultor) com senhas Bcrypt
5. Imóvel de demonstração ativo alinhado ao design system
6. Contato pós-venda para validação de aniversário de escritura
"""
import sys
import os
from datetime import date, datetime, timezone
import bcrypt

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.property import Property
from app.models.objection import ObjectionTag
from app.models.contact import Contact
from app.models.settings import Settings


def hash_password(password: str) -> str:
    """Gera hash Bcrypt seguro para a senha."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def seed_database():
    """Popula o banco de dados com dados iniciais para desenvolvimento."""
    db = SessionLocal()
    try:
        print("🌱 Iniciando seed do banco de dados Fecho...")

        # 1. Verifica ou cria o Tenant de demonstração
        tenant = db.query(Tenant).filter_by(slug="fecho-prime").first()
        if not tenant:
            tenant = Tenant(
                nome="Fecho Prime Real Estate",
                slug="fecho-prime",
                nif="512345678",
                telefone="+351 210 000 000",
                email="contato@fecho-prime.pt",
                morada="Avenida da Liberdade, 100, Lisboa",
                ativo=True,
            )
            db.add(tenant)
            db.flush()
            print(f"  ✓ Agência criada: {tenant.nome} (ID: {tenant.id})")
        else:
            print(f"  ℹ Agência já existente: {tenant.nome} (ID: {tenant.id})")

        # 2. Parametrizações da Agência (Settings)
        settings = db.query(Settings).filter_by(agencia_id=tenant.id).first()
        if not settings:
            settings = Settings(
                agencia_id=tenant.id,
                spread_referencia=0.85,
                taxa_stress=1.50,
                prazo_max_financiamento_anos=30,
                percentual_financiamento_max=85.00,
                hora_notificacao_aniversario="09:00",
            )
            db.add(settings)
            print("  ✓ Parametrizações da agência criadas (Spread: 0.85%, Notificação: 09:00)")

        # 3. Catálogo de Objeções Padronizadas
        initial_tags = [
            ("Preço Elevado", "preco"),
            ("Área Inferior ao Esperado", "dimensao"),
            ("Ruído da Rua / Zona Movimentada", "localizacao"),
            ("Falta de Garagem / Estacionamento", "caracteristica"),
            ("Exposição Solar Fraca", "caracteristica"),
            ("Necessita de Obras Profundas", "estado"),
            ("Piso Elevado sem Elevador", "caracteristica"),
        ]

        for tag_nome, categoria in initial_tags:
            existing_tag = db.query(ObjectionTag).filter_by(
                agencia_id=tenant.id, tag=tag_nome
            ).first()
            if not existing_tag:
                new_tag = ObjectionTag(
                    agencia_id=tenant.id,
                    tag=tag_nome,
                    categoria=categoria,
                    ativo=True,
                )
                db.add(new_tag)
        print(f"  ✓ Catálogo de objeções padronizadas configurado ({len(initial_tags)} tags)")

        # 4. Usuários de Demonstração (Diretora e Consultor)
        # Diretor: diretor@fecho.pt / senha_segura_diretor
        diretor = db.query(User).filter_by(email="diretor@fecho.pt").first()
        if not diretor:
            diretor = User(
                agencia_id=tenant.id,
                nome="Marta Silva",
                email="diretor@fecho.pt",
                password_hash=hash_password("senha_segura_diretor"),
                role="diretor",
                telemovel="+351 912 345 678",
                ativo=True,
            )
            db.add(diretor)
            print("  ✓ Usuário Diretor criado: diretor@fecho.pt (senha: senha_segura_diretor)")
        else:
            print("  ℹ Usuário Diretor já existente.")

        # Consultor: consultor@fecho.pt / senha_segura_consultor
        consultor = db.query(User).filter_by(email="consultor@fecho.pt").first()
        if not consultor:
            consultor = User(
                agencia_id=tenant.id,
                nome="João Santos",
                email="consultor@fecho.pt",
                password_hash=hash_password("senha_segura_consultor"),
                role="consultor",
                telemovel="+351 923 456 789",
                ativo=True,
            )
            db.add(consultor)
            db.flush()
            print("  ✓ Usuário Consultor criado: consultor@fecho.pt (senha: senha_segura_consultor)")
        else:
            print("  ℹ Usuário Consultor já existente.")

        # 5. Imóvel de Demonstração Ativo
        imovel = db.query(Property).filter_by(
            agencia_id=tenant.id, titulo="T3 Duplex Avenida da Liberdade"
        ).first()
        if not imovel:
            imovel = Property(
                agencia_id=tenant.id,
                consultor_id=consultor.id if consultor else 1,
                titulo="T3 Duplex Avenida da Liberdade",
                descricao="Exclusivo apartamento duplex com acabamentos nobres em mármore e madeira maciça, terraço privativo e vista panorâmica sobre a cidade.",
                tipologia="T3",
                preco=2850000.00,
                morada="Avenida da Liberdade, 250",
                concelho="Lisboa",
                distrito="Lisboa",
                regiao_fiscal="continente",
                area_bruta=215.50,
                status="Ativo",
                nome_proprietario="Manuel Fernandes",
                telefone_proprietario="+351 961 112 233",
            )
            db.add(imovel)
            db.flush()
            print(f"  ✓ Imóvel criado: {imovel.titulo} (Valor: € 2.850.000, Status: {imovel.status})")
        else:
            print(f"  ℹ Imóvel de demonstração já existente: {imovel.titulo}")

        # 6. Contato pós-venda para esfera de influência / aniversário de escritura
        hoje = date.today()
        # Define a data da escritura exatamente 1 ano antes da data de hoje para testar aniversariante do dia
        data_escritura_aniversario = date(hoje.year - 1, hoje.month, hoje.day)

        contato = db.query(Contact).filter_by(
            agencia_id=tenant.id, email="carlos.oliveira@example.com"
        ).first()
        if not contato:
            contato = Contact(
                agencia_id=tenant.id,
                consultor_id=consultor.id if consultor else 1,
                property_id=imovel.id if imovel else None,
                nome="Carlos Eduardo Oliveira",
                telemovel="+351 934 567 890",
                email="carlos.oliveira@example.com",
                tipo="comprador",
                data_escritura=data_escritura_aniversario,
                anonimizado=False,
                notas="Adquiriu imóvel no ano anterior. Cliente VIP da agência.",
            )
            db.add(contato)
            print(f"  ✓ Contato pós-venda criado: {contato.nome} (Escritura: {contato.data_escritura})")

        db.commit()
        print("✅ Seed concluído com sucesso!")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro durante a execução do seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
