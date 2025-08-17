# app/mappers/credential_mapper.py
from app.db.models import Credential
from app.dtos.credential_dto import CredentialDTO

def to_credential_dto(c: Credential) -> CredentialDTO:
    return CredentialDTO.from_orm(c)
