from app.models.chat_models import ChatResponseModel
from app.dtos.chat_dto import ChatDTO


def map_chat_response_to_dto(model: ChatResponseModel) -> ChatDTO:
    # Usa model_validate para Pydantic v2
    return ChatDTO.model_validate(model)
