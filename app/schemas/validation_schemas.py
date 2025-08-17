# app/schemas/validation_schemas.py
LLM_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool":   {"type": "string"},
                    "params": {"type": "object"}
                },
                "required": ["tool", "params"]
            }
        },
        "final_output": {"type": "string"}
    },
    "required": ["steps", "final_output"]
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "oneOf": [
                    {"required": ["node_id", "action_id"]},
                    {"required": ["type", "condition", "next_on_true", "next_on_false"]}
                ]
            }
        }
    },
    "required": ["steps"],
    "additionalProperties": False,
}
