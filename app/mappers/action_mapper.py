from app.db.models import Action
from app.dtos.action_dto import ActionDTO

def to_action_dto(action: Action) -> ActionDTO:
    return ActionDTO.from_orm(action)

