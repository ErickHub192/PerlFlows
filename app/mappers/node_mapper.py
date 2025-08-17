from app.db.models import Node
from app.dtos.node_dto import NodeDTO
from app.dtos.action_dto import ActionDTO

def to_node_dto(node: Node) -> NodeDTO:
    actions = [ActionDTO.from_orm(a) for a in getattr(node, "actions", [])]
    return NodeDTO(
        node_id=node.node_id,
        name=node.name,
        node_type=getattr(node.node_type, "value", node.node_type),
        default_auth=node.default_auth,
        use_case=node.use_case,
        usage_mode=getattr(node, "usage_mode", None),
        actions=actions,
    )

