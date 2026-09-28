"""
Serviço de Negócio para Gestão de Imóveis (PropertyService) - Fecho (fecho.pt).

Regras de Negócio e Segurança:
1. Isolamento Multi-tenant: Todas as consultas filtram obrigatoriamente por 'agencia_id'.
2. Máquina de Estados: Ciclo de vida estrito 'Ativo' -> 'Reservado' -> 'Vendido' (e reversão 'Reservado' -> 'Ativo').
3. Validação dos 3 campos de Fecho: Transição para 'Vendido' exige obrigatoriamente:
   - nome_comprador
   - telefone_comprador
   - data_escritura
4. Alimentação da Esfera de Influência: Ao transitar para 'Vendido', gera automaticamente o contato em Contact.
5. RBAC: Consultores operam na carteira; Diretores possuem gestão irrestrita na agência.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.contact import Contact
from app.models.property import Property
from app.models.user import User
from app.schemas.property_schema import PropertyCreate, PropertyTransitionStatus, PropertyUpdate


class PropertyService:
    """Camada de serviços e regras de negócio para imóveis."""

    @staticmethod
    def list_properties(
        db: Session,
        agencia_id: int,
        status_filter: Optional[str] = None,
        tipologia: Optional[str] = None,
        consultor_id: Optional[int] = None,
        busca: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Property], int]:
        """
        Lista imóveis com isolamento multi-tenant obrigatório por agencia_id.
        Suporta filtros por status, tipologia, consultor e termo de busca.
        """
        query = db.query(Property).options(joinedload(Property.consultor)).filter(
            Property.agencia_id == agencia_id
        )

        if status_filter:
            status_clean = status_filter.strip().capitalize()
            query = query.filter(Property.status == status_clean)

        if tipologia:
            query = query.filter(Property.tipologia == tipologia.strip().upper())

        if consultor_id:
            query = query.filter(Property.consultor_id == consultor_id)

        if busca:
            termo = f"%{busca.strip()}%"
            query = query.filter(
                or_(
                    Property.titulo.ilike(termo),
                    Property.morada.ilike(termo),
                    Property.concelho.ilike(termo),
                    Property.distrito.ilike(termo),
                    Property.nome_proprietario.ilike(termo),
                )
            )

        total = query.count()
        properties = query.order_by(Property.created_at.desc()).offset(skip).limit(limit).all()
        return properties, total

    @staticmethod
    def get_property_by_id(db: Session, property_id: int, agencia_id: int) -> Property:
        """
        Obtém um imóvel pelo ID garantindo que pertence à agência do usuário (Multi-tenant).
        """
        property_obj = db.query(Property).options(joinedload(Property.consultor)).filter(
            Property.id == property_id,
            Property.agencia_id == agencia_id
        ).first()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imóvel #{property_id} não encontrado na sua agência."
            )

        return property_obj

    @staticmethod
    def create_property(
        db: Session,
        property_in: PropertyCreate,
        current_user: User
    ) -> Property:
        """
        Cadastra um novo imóvel na carteira da agência.
        Status inicial é obrigatoriamente 'Ativo'.
        """
        # Se for consultor, o imóvel fica associado a ele. Se for diretor, pode atribuir a outro da mesma agência.
        target_consultor_id = current_user.id
        if current_user.role == "diretor" and property_in.consultor_id:
            # Valida se o consultor indicado pertence à mesma agência
            consultor = db.query(User).filter(
                User.id == property_in.consultor_id,
                User.agencia_id == current_user.agencia_id,
                User.ativo == True
            ).first()
            if not consultor:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Consultor indicado não encontrado ou inativo nesta agência."
                )
            target_consultor_id = consultor.id

        new_property = Property(
            agencia_id=current_user.agencia_id,
            consultor_id=target_consultor_id,
            titulo=property_in.titulo.strip(),
            descricao=property_in.descricao.strip() if property_in.descricao else None,
            tipologia=property_in.tipologia.strip().upper(),
            preco=property_in.preco,
            morada=property_in.morada.strip() if property_in.morada else None,
            concelho=property_in.concelho.strip() if property_in.concelho else None,
            distrito=property_in.distrito.strip() if property_in.distrito else None,
            regiao_fiscal=property_in.regiao_fiscal.strip().lower(),
            area_bruta=property_in.area_bruta,
            status="Ativo",
            nome_proprietario=property_in.nome_proprietario.strip(),
            telefone_proprietario=property_in.telefone_proprietario.strip(),
        )

        db.add(new_property)
        db.commit()
        db.refresh(new_property)
        return new_property

    @staticmethod
    def update_property(
        db: Session,
        property_id: int,
        property_update: PropertyUpdate,
        current_user: User
    ) -> Property:
        """
        Atualiza dados cadastrais de um imóvel.
        Consultores só podem atualizar seus próprios imóveis; Diretores atualizam qualquer da agência.
        Não altera 'status' diretamente (deve usar transition_status).
        """
        property_obj = PropertyService.get_property_by_id(db, property_id, current_user.agencia_id)

        # Regra RBAC para edição
        if current_user.role == "consultor" and property_obj.consultor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o consultor responsável ou a direção podem editar este imóvel."
            )

        update_data = property_update.model_dump(exclude_unset=True)

        # Consultor reatribuído (apenas diretor pode trocar)
        if "consultor_id" in update_data and update_data["consultor_id"]:
            if current_user.role != "diretor":
                del update_data["consultor_id"]
            else:
                consultor = db.query(User).filter(
                    User.id == update_data["consultor_id"],
                    User.agencia_id == current_user.agencia_id,
                    User.ativo == True
                ).first()
                if not consultor:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Consultor indicado não pertence a esta agência."
                    )

        for field, value in update_data.items():
            if field in ("titulo", "descricao", "morada", "concelho", "distrito", "nome_proprietario", "telefone_proprietario"):
                setattr(property_obj, field, value.strip() if isinstance(value, str) else value)
            elif field == "tipologia" and value:
                setattr(property_obj, field, value.strip().upper())
            elif field == "regiao_fiscal" and value:
                setattr(property_obj, field, value.strip().lower())
            else:
                setattr(property_obj, field, value)

        db.commit()
        db.refresh(property_obj)
        return property_obj

    @staticmethod
    def transition_status(
        db: Session,
        property_id: int,
        transition_data: PropertyTransitionStatus,
        current_user: User
    ) -> Property:
        """
        Aplica a Máquina de Estados Estrita do FSD:
        - Ciclo: 'Ativo' -> 'Reservado' -> 'Vendido' (e reversão 'Reservado' -> 'Ativo').
        - 'Vendido' é estado terminal de transação.
        - Transição para 'Vendido' exige OBRIGATORIAMENTE os 3 campos:
            1. nome_comprador
            2. telefone_comprador
            3. data_escritura
        - Ao vender com sucesso, gera automaticamente o registro em Contact (Esfera de Influência).
        """
        property_obj = PropertyService.get_property_by_id(db, property_id, current_user.agencia_id)

        # Consultores só transitam status dos seus próprios imóveis; Diretores transitam de qualquer imóvel da agência
        if current_user.role == "consultor" and property_obj.consultor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o consultor responsável ou a direção podem alterar o estado deste imóvel."
            )

        current_status = property_obj.status
        target_status = transition_data.novo_status

        # 1. Se já está Vendido, é estado terminal
        if current_status == "Vendido":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imóvel já se encontra com a venda concretizada (estado terminal). Não é permitida nova alteração de estado."
            )

        # 2. Se o status alvo for igual ao atual
        if current_status == target_status:
            return property_obj

        # 3. Validação de transições permitidas
        # Ativo -> Reservado | Vendido
        # Reservado -> Ativo | Vendido
        if current_status == "Ativo" and target_status not in ("Reservado", "Vendido"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transição inválida de '{current_status}' para '{target_status}'."
            )

        if current_status == "Reservado" and target_status not in ("Ativo", "Vendido"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transição inválida de '{current_status}' para '{target_status}'."
            )

        # 4. Regra crucial: Transição para 'Vendido' exige os 3 campos
        if target_status == "Vendido":
            nome_comprador = transition_data.nome_comprador.strip() if transition_data.nome_comprador else None
            tel_comprador = transition_data.telefone_comprador.strip() if transition_data.telefone_comprador else None
            data_escritura = transition_data.data_escritura

            erros = []
            if not nome_comprador or len(nome_comprador) < 2:
                erros.append("Nome do Comprador é obrigatório.")
            if not tel_comprador or len(tel_comprador) < 6:
                erros.append("Telemóvel do Comprador é obrigatório.")
            if not data_escritura:
                erros.append("Data da Escritura é obrigatória.")

            if erros:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A transição para 'Vendido' exige obrigatoriamente os 3 campos: " + "; ".join(erros)
                )

            # Persiste os 3 campos no imóvel
            property_obj.status = "Vendido"
            property_obj.nome_comprador = nome_comprador
            property_obj.telefone_comprador = tel_comprador
            property_obj.data_escritura = data_escritura

            # Cria ou atualiza o contato pós-venda na Esfera de Influência
            comprador_contato = Contact(
                agencia_id=property_obj.agencia_id,
                consultor_id=property_obj.consultor_id,
                property_id=property_obj.id,
                nome=nome_comprador,
                telemovel=tel_comprador,
                tipo="comprador",
                data_escritura=data_escritura,
                notas=f"Comprador do imóvel '{property_obj.titulo}' (#{property_obj.id}) por escritura celebrada em {data_escritura.strftime('%d/%m/%Y')}."
            )
            db.add(comprador_contato)

        elif target_status == "Reservado":
            property_obj.status = "Reservado"

        elif target_status == "Ativo":
            # Reversão de Reservado para Ativo
            property_obj.status = "Ativo"

        db.commit()
        db.refresh(property_obj)
        return property_obj

    @staticmethod
    def delete_property(db: Session, property_id: int, current_user: User) -> None:
        """
        Exclui um imóvel da carteira.
        Apenas permitida se não houver visitas registradas e se o usuário for diretor ou o consultor responsável.
        """
        property_obj = PropertyService.get_property_by_id(db, property_id, current_user.agencia_id)

        if current_user.role == "consultor" and property_obj.consultor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o consultor responsável ou a direção podem eliminar este imóvel."
            )

        if len(property_obj.visits) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este imóvel possui visitas e feedback registrados no histórico e não pode ser eliminado."
            )

        db.delete(property_obj)
        db.commit()
