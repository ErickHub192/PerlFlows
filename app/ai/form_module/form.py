# app/ai/form_module/form.py


#Maybe puede ser útil en un futuro para el cacheo de los schemas, y extenderlo a un service propio si se vuelve mas complejo.
#Nota: Moverlo de esta ruta

from typing import Dict, List
from app.services.iform_service import IFormService
from app.dtos.form_schema_dto import FormSchemaDTO

class FormModule:
    """
    Genera el JSON Schema de un nodo consultando el FormService
    (que a su vez va a la base de datos vía tu capa n‑layers).
    """

    def __init__(self, form_service: IFormService):
        self.form_service = form_service
        # Cache local opcional: { (node, action): FormSchemaDTO }
        self._cache: Dict[str, FormSchemaDTO] = {}

    def get_form_schema_for_node(self, node_name: str, action: str = "") -> FormSchemaDTO:
        key = f"{node_name}|{action}"
        if key in self._cache:
            return self._cache[key]

        # Llama al service que lee desde la BD
        schema = self.form_service.get_schema(node_name, action or None)

        # Guarda en cache (puedes añadir TTL si quieres)
        self._cache[key] = schema
        return schema
