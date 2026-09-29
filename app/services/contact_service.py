"""
Serviço de Negócio para Contatos, Esfera de Influência e Pós-Venda.
Conforme FSD:
- Isolamento rigoroso por agencia_id.
- Gestão de compradores e contatos pós-venda.
- Detecção de aniversariantes da data de celebração de escritura (notificações às 09:00).
- Geração de mensagens dinâmicas de pós-venda para WhatsApp em 1 clique (Deep Link).
- Procedimento de conformidade RGPD para anonimização ('Cliente Anonimizado').
"""
from datetime import date, datetime
import re
from typing import List, Optional, Tuple
import urllib.parse

from fastapi import HTTPException, status
from sqlalchemy import and_, extract, or_
from sqlalchemy.orm import Session, joinedload

from app.models.contact import Contact
from app.models.log import Log
from app.models.property import Property
from app.models.user import User
from app.schemas.contact_schema import (
    AnonymizeResponse,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    ContactWhatsAppResponse,
)


class ContactService:

    @staticmethod
    def _sanitize_phone_for_whatsapp(phone: str) -> str:
        """
        Higieniza número de telefone para o padrão internacional do WhatsApp:
        - Remove caracteres não-numéricos;
        - Adiciona DDI de Portugal (351) se for número móvel português com 9 dígitos iniciando por 9.
        """
        digits = re.sub(r"\D", "", phone or "")
        if not digits:
            return ""
        # Caso padrão português de telemóvel (ex.: 912345678 -> 351912345678)
        if len(digits) == 9 and digits.startswith("9"):
            return f"351{digits}"
        # Se começar com 00, remove o 00
        if digits.startswith("00"):
            digits = digits[2:]
        return digits

    @staticmethod
    def _enrich_contact_response(contact: Contact, target_date: Optional[date] = None) -> ContactResponse:
        """
        Enriquece a entidade Contact com métricas de tempo decorrido e aniversário.
        """
        ref_date = target_date or date.today()
        anos_escritura = None
        is_aniversario = False

        if contact.data_escritura:
            d = contact.data_escritura
            # Anos decorridos desde a data da escritura
            anos_calc = ref_date.year - d.year
            if (ref_date.month, ref_date.day) < (d.month, d.day):
                anos_calc -= 1
            anos_escritura = max(0, anos_calc)

            # É aniversário hoje se dia e mês coincidem (e não foi celebrado hoje pela primeira vez no mesmo ano)
            if not contact.anonimizado and d.month == ref_date.month and d.day == ref_date.day and ref_date.year > d.year:
                is_aniversario = True

        consultor_nome = contact.consultor.nome if contact.consultor else None
        property_titulo = contact.property.titulo if contact.property else None

        return ContactResponse(
            id=contact.id,
            agencia_id=contact.agencia_id,
            consultor_id=contact.consultor_id,
            consultor_nome=consultor_nome,
            property_id=contact.property_id,
            property_titulo=property_titulo,
            nome=contact.nome,
            telemovel=contact.telemovel,
            email=contact.email,
            tipo=contact.tipo,
            data_escritura=contact.data_escritura,
            anonimizado=contact.anonimizado,
            notas=contact.notas,
            anos_escritura=anos_escritura,
            is_aniversario_hoje=is_aniversario,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )

    @staticmethod
    def get_contact_by_id(db: Session, contact_id: int, current_user: User) -> Contact:
        """
        Busca um contato por ID com validação de agência e privilégios.
        """
        query = db.query(Contact).options(
            joinedload(Contact.consultor),
            joinedload(Contact.property)
        ).filter(
            Contact.id == contact_id,
            Contact.agencia_id == current_user.agencia_id
        )

        contact = query.first()
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contato #{contact_id} não encontrado na sua agência."
            )

        # Consultor só acessa contatos que estão sob sua gestão
        if current_user.role == "consultor" and contact.consultor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o consultor responsável ou a direção podem consultar este contato."
            )

        return contact

    @staticmethod
    def create_contact(db: Session, contact_in: ContactCreate, current_user: User) -> ContactResponse:
        """
        Cria um contato na esfera de influência ou pós-venda da agência.
        """
        target_consultor_id = current_user.id
        if current_user.role == "diretor" and contact_in.consultor_id:
            # Valida se o consultor existe na agência
            consultor = db.query(User).filter(
                User.id == contact_in.consultor_id,
                User.agencia_id == current_user.agencia_id,
                User.ativo == True
            ).first()
            if not consultor:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Consultor indicado não encontrado ou inativo nesta agência."
                )
            target_consultor_id = consultor.id

        # Valida se imóvel existe na agência, se informado
        if contact_in.property_id:
            prop = db.query(Property).filter(
                Property.id == contact_in.property_id,
                Property.agencia_id == current_user.agencia_id
            ).first()
            if not prop:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Imóvel associado não encontrado na sua agência."
                )

        new_contact = Contact(
            agencia_id=current_user.agencia_id,
            consultor_id=target_consultor_id,
            property_id=contact_in.property_id,
            nome=contact_in.nome.strip(),
            telemovel=contact_in.telemovel.strip(),
            email=contact_in.email.strip().lower() if contact_in.email else None,
            tipo=contact_in.tipo.strip().lower(),
            data_escritura=contact_in.data_escritura,
            notas=contact_in.notas.strip() if contact_in.notas else None,
            anonimizado=False,
        )

        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)

        return ContactService._enrich_contact_response(new_contact)

    @staticmethod
    def update_contact(
        db: Session,
        contact_id: int,
        contact_in: ContactUpdate,
        current_user: User
    ) -> ContactResponse:
        """
        Atualiza os dados de um contato existente.
        Contatos anonimizados não podem ter dados pessoais alterados.
        """
        contact = ContactService.get_contact_by_id(db, contact_id, current_user)

        if contact.anonimizado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este contato foi anonimizado nos termos do RGPD e seus dados pessoais não podem ser modificados."
            )

        if contact_in.nome is not None:
            contact.nome = contact_in.nome.strip()
        if contact_in.telemovel is not None:
            contact.telemovel = contact_in.telemovel.strip()
        if contact_in.email is not None:
            contact.email = contact_in.email.strip().lower() if contact_in.email.strip() else None
        if contact_in.tipo is not None:
            contact.tipo = contact_in.tipo.strip().lower()
        if contact_in.data_escritura is not None:
            contact.data_escritura = contact_in.data_escritura
        if contact_in.notas is not None:
            contact.notas = contact_in.notas.strip() if contact_in.notas.strip() else None

        if contact_in.property_id is not None:
            if contact_in.property_id == 0:
                contact.property_id = None
            else:
                prop = db.query(Property).filter(
                    Property.id == contact_in.property_id,
                    Property.agencia_id == current_user.agencia_id
                ).first()
                if not prop:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Imóvel associado não encontrado na sua agência."
                    )
                contact.property_id = prop.id

        if current_user.role == "diretor" and contact_in.consultor_id is not None:
            consultor = db.query(User).filter(
                User.id == contact_in.consultor_id,
                User.agencia_id == current_user.agencia_id,
                User.ativo == True
            ).first()
            if not consultor:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Consultor indicado não encontrado ou inativo nesta agência."
                )
            contact.consultor_id = consultor.id

        db.commit()
        db.refresh(contact)

        return ContactService._enrich_contact_response(contact)

    @staticmethod
    def list_contacts(
        db: Session,
        current_user: User,
        query_str: Optional[str] = None,
        tipo: Optional[str] = None,
        apenas_aniversario_hoje: bool = False,
        consultor_id: Optional[int] = None,
        target_date: Optional[date] = None,
    ) -> Tuple[List[ContactResponse], int, int]:
        """
        Lista contatos da esfera de influência com isolamento multi-tenant e filtros.
        Retorna (lista_enriquecida, total_itens, total_aniversariantes_hoje).
        """
        ref_date = target_date or date.today()

        base_query = db.query(Contact).options(
            joinedload(Contact.consultor),
            joinedload(Contact.property)
        ).filter(
            Contact.agencia_id == current_user.agencia_id
        )

        # Regra de perfil: consultor vê seus contatos; diretor vê todos ou filtra
        if current_user.role == "consultor":
            base_query = base_query.filter(Contact.consultor_id == current_user.id)
        elif consultor_id:
            base_query = base_query.filter(Contact.consultor_id == consultor_id)

        # Filtro textual (nome, telefone, email)
        if query_str and query_str.strip():
            term = f"%{query_str.strip()}%"
            base_query = base_query.filter(
                or_(
                    Contact.nome.ilike(term),
                    Contact.telemovel.ilike(term),
                    Contact.email.ilike(term),
                    Contact.notas.ilike(term),
                )
            )

        # Filtro por tipo
        if tipo and tipo.strip():
            base_query = base_query.filter(Contact.tipo == tipo.strip().lower())

        contacts = base_query.order_by(Contact.nome.asc()).all()

        enriched: List[ContactResponse] = []
        aniversariantes_hoje_count = 0

        for c in contacts:
            resp = ContactService._enrich_contact_response(c, ref_date)
            if resp.is_aniversario_hoje:
                aniversariantes_hoje_count += 1

            if apenas_aniversario_hoje:
                if resp.is_aniversario_hoje:
                    enriched.append(resp)
            else:
                enriched.append(resp)

        return enriched, len(enriched), aniversariantes_hoje_count

    @staticmethod
    def get_anniversary_contacts(
        db: Session,
        current_user: User,
        target_date: Optional[date] = None
    ) -> List[ContactResponse]:
        """
        Obtém os contatos que celebram aniversário da escritura na data de referência (hoje).
        Utilizado pelo alerta das 09:00 e pelo card em destaque no PWA.
        """
        items, _, _ = ContactService.list_contacts(
            db=db,
            current_user=current_user,
            apenas_aniversario_hoje=True,
            target_date=target_date,
        )
        return items

    @staticmethod
    def generate_whatsapp_message(
        db: Session,
        contact_id: int,
        current_user: User,
        tipo_mensagem: str = "aniversario_escritura",
        custom_texto: Optional[str] = None
    ) -> ContactWhatsAppResponse:
        """
        Gera mensagem dinâmica estruturada em tom Editorial PropTech Luxury
        e Deep Link para disparo em 1 clique para o WhatsApp do cliente.
        """
        contact = ContactService.get_contact_by_id(db, contact_id, current_user)

        if contact.anonimizado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível gerar mensagem de WhatsApp para um contato anonimizado pelo RGPD."
            )

        clean_phone = ContactService._sanitize_phone_for_whatsapp(contact.telemovel)
        if not clean_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O contato não possui um número de telemóvel válido para envio de WhatsApp."
            )

        # Dados para interpolação
        nome = contact.nome.strip()
        consultor_nome = contact.consultor.nome if contact.consultor else current_user.nome
        prop_titulo = contact.property.titulo if contact.property else "o seu imóvel"

        # Cálculo de anos
        anos = 1
        if contact.data_escritura:
            hoje = date.today()
            calc = hoje.year - contact.data_escritura.year
            anos = max(1, calc)

        plural_ano = "ano" if anos == 1 else "anos"

        # Se custom_texto fornecido, usa-o
        if custom_texto and custom_texto.strip():
            texto = custom_texto.strip()
        else:
            tipo_lower = (tipo_mensagem or "aniversario_escritura").strip().lower()
            if tipo_lower == "aniversario_escritura":
                texto = (
                    f"Olá {nome}! Hoje comemora-se {anos} {plural_ano} desde a celebração da escritura "
                    f"de {prop_titulo}.\n\n"
                    f"Queria felicitar-lhe pessoalmente por este aniversário e saber como tem sido "
                    f"a experiência em casa. Desejo-lhe as maiores felicidades!\n\n"
                    f"Estou sempre ao dispor para qualquer apoio imobiliário.\n\n"
                    f"Um cumprimento cordial,\n{consultor_nome} | Fecho"
                )
            elif tipo_lower == "pos_venda_geral":
                texto = (
                    f"Olá {nome}, tudo bem consigo?\n\n"
                    f"Entro em contacto para saber como tem corrido a adaptação a {prop_titulo} "
                    f"e se tudo está a correr dentro das suas melhores expectativas.\n\n"
                    f"Conte sempre comigo para recomendações ou esclarecimentos sobre o mercado imobiliário.\n\n"
                    f"Um abraço,\n{consultor_nome} | Fecho"
                )
            elif tipo_lower == "valorizacao_patrimonial":
                texto = (
                    f"Olá {nome}, espero que esteja tudo bem!\n\n"
                    f"O mercado imobiliário na envolvente de {prop_titulo} tem apresentado uma dinâmica "
                    f"muito positiva este trimestre.\n\n"
                    f"Se tiver curiosidade, terei todo o prazer em preparar uma atualização da avaliação "
                    f"patrimonial estimada da sua casa, sem qualquer encargo ou compromisso.\n\n"
                    f"Diga-me se for do seu interesse!\n\n"
                    f"Atenciosamente,\n{consultor_nome} | Fecho"
                )
            elif tipo_lower == "convite_cafe":
                texto = (
                    f"Olá {nome}! Como tem passado?\n\n"
                    f"Já lá vai algum tempo desde que celebrámos o negócio de {prop_titulo}. "
                    f"Gostava de lhe pagar um café breve um destes dias para pôr a conversa em dia.\n\n"
                    f"Tem disponibilidade para um breve encontro esta semana?\n\n"
                    f"Um abraço amigo,\n{consultor_nome} | Fecho"
                )
            else:
                # Padrão consultivo
                texto = (
                    f"Olá {nome}, tudo bem consigo? Daqui fala {consultor_nome} da Fecho. "
                    f"Fico à sua inteira disposição relativamente a {prop_titulo}."
                )

        encoded_text = urllib.parse.quote(texto)
        whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_text}"

        return ContactWhatsAppResponse(
            contact_id=contact.id,
            contact_nome=contact.nome,
            telemovel=contact.telemovel,
            tipo_mensagem=tipo_mensagem,
            texto=texto,
            whatsapp_url=whatsapp_url,
        )

    @staticmethod
    def anonymize_contact(
        db: Session,
        contact_id: int,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> AnonymizeResponse:
        """
        Executa a rotina de anonimização conforme RGPD (Regulamento Geral sobre a Proteção de Dados):
        - Substitui nome por 'Cliente Anonimizado';
        - Zera telefone ('000000000');
        - Remove e-mail;
        - Marca flag anonimizado=True;
        - Mantém histórico relacional com o imóvel/escritura para integridade estatística da agência;
        - Registra evento de auditoria no audit_logs (sem dados sensíveis).
        """
        contact = ContactService.get_contact_by_id(db, contact_id, current_user)

        if contact.anonimizado:
            return AnonymizeResponse(
                contact_id=contact.id,
                status="ja_anonimizado",
                mensagem="Este contato já se encontrava anonimizado no sistema.",
                nome=contact.nome,
                anonimizado=True,
            )

        # Aplica o método de conformidade do modelo
        contact.anonimizar_rgpd()

        # Grava trilha de auditoria em audit_logs
        audit_log = Log(
            agencia_id=current_user.agencia_id,
            user_id=current_user.id,
            acao="RGPD_ANONIMIZACAO",
            entidade="contact",
            entidade_id=contact.id,
            detalhes=f"Contato #{contact.id} anonimizado em conformidade com o RGPD pelo utilizador {current_user.email} (ID #{current_user.id}).",
            ip_address=client_ip,
        )
        db.add(audit_log)

        db.commit()
        db.refresh(contact)

        return AnonymizeResponse(
            contact_id=contact.id,
            status="anonimizado_com_sucesso",
            mensagem="Os dados pessoais do comprador/contato foram permanentemente anonimizados conforme o RGPD, mantendo o histórico transacional.",
            nome=contact.nome,
            anonimizado=True,
        )

    @staticmethod
    def delete_contact(db: Session, contact_id: int, current_user: User) -> None:
        """
        Remove um contato da esfera de influência.
        Se o contato estiver atrelado a um imóvel como comprador pós-venda,
        prioriza a anonimização para manter integridade das métricas do imóvel.
        """
        contact = ContactService.get_contact_by_id(db, contact_id, current_user)

        # Se for comprador vinculado a um imóvel, exige anonimização em vez de exclusão física
        if contact.property_id and contact.tipo == "comprador":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Compradores vinculados à escritura de um imóvel não devem ser excluídos fisicamente para não quebrar o histórico de vendas. Utilize a rota de anonimização conforme RGPD."
            )

        db.delete(contact)
        db.commit()
