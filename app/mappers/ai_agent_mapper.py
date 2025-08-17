from app.db.models import AIAgent
from app.dtos.ai_agent_dto import AIAgentDTO

def to_ai_agent_dto(agent: AIAgent) -> AIAgentDTO:
    return AIAgentDTO.from_orm(agent)
