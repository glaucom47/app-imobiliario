"""
Módulo de modelos relacionais SQLAlchemy da aplicação Fecho.
Exporta todas as entidades para permitir mapeamento e detecção automática pelo Alembic.
"""
from database.connection import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.property import Property
from app.models.visit import Visit
from app.models.objection import ObjectionTag, VisitObjection
from app.models.contact import Contact
from app.models.settings import Settings
from app.models.log import Log

__all__ = [
    "Base",
    "Tenant",
    "User",
    "Property",
    "Visit",
    "ObjectionTag",
    "VisitObjection",
    "Contact",
    "Settings",
    "Log",
]
