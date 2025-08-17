from app.db.models import Parameter
from app.dtos.parameter_dto import ParameterDTO

def to_parameter_dto(param: Parameter) -> ParameterDTO:
    return ParameterDTO.from_orm(param)
