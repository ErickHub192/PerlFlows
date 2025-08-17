# 🚀 MEJORAS FUTURAS DEL SISTEMA

## 📝 DISCOVERY CON RAG/EMBEDDINGS

### ❌ **PROBLEMA ACTUAL:**
El sistema actual usa mapeo estático para discovery de archivos e intenciones:

```python
# En UniversalDiscoveryProvider
intent_file_mapping = {
    "inventory": ["inventory"],
    "inventario": ["inventory"],
    "stock": ["inventory"],
    "productos": ["inventory"],
    # ... más mapeos hardcodeados
}

# En CAGDiscoveryProvider  
node_auth_mapping = {
    "google_sheets": ["oauth2_google_sheets"],
    "google_drive": ["oauth2_google_drive"],
    # ... más mapeos hardcodeados
}
```

### ✅ **SOLUCIÓN FUTURA CON RAG:**

#### **1. Usar la tabla `nodes` existente con embeddings**

La tabla `nodes` ya tiene metadata rica de todos los conectores:
- `node_id`, `name`, `description` 
- `actions` con descripciones detalladas
- `parameters` con contexto de uso

**Implementación recomendada:**
```python
# 1. Generar embeddings para cada nodo
for node in nodes_table:
    text_to_embed = f"{node.name} {node.description} {node.actions}"
    embedding = generate_embedding(text_to_embed)
    node.embedding = embedding  # Nueva columna

# 2. Discovery basado en similaridad semántica
user_intent_embedding = generate_embedding(user_intent)
similar_nodes = find_similar_nodes(user_intent_embedding, threshold=0.7)
```

#### **2. Eliminar mapeos estáticos**

**Archivos a refactorizar:**
- `app/workflow_engine/discovery/universal_discovery.py`
- `app/workflow_engine/discovery/cag_discovery.py`
- `app/services/universal_discovery_service.py`

**Reemplazar:**
```python
# ❌ Mapeo estático actual
def _extract_file_types_from_intent(self, intent: str) -> List[str]:
    intent_file_mapping = {
        "inventory": ["inventory"],
        "contactos": ["contacts"],
        # ... hardcoded mappings
    }

# ✅ RAG/Embeddings approach
async def _discover_relevant_file_types(self, intent: str) -> List[str]:
    intent_embedding = await self.embedding_service.generate(intent)
    similar_patterns = await self.embedding_service.find_similar(
        intent_embedding, 
        collection="file_patterns",
        threshold=0.75
    )
    return [pattern.file_type for pattern in similar_patterns]
```

#### **3. Discovery de nodos con embeddings**

```python
# ✅ En CAGDiscoveryProvider futuro
async def discover_capabilities(self, intent: str, user_id: int, context: Dict[str, Any] = None):
    # Usar embeddings en lugar de NodeSelectionService tradicional
    intent_embedding = await self.embedding_service.generate(intent)
    
    # Buscar nodos similares en la tabla con embeddings
    similar_nodes = await self.node_repository.find_by_embedding_similarity(
        intent_embedding, 
        threshold=0.7,
        limit=10
    )
    
    capabilities = []
    for node in similar_nodes:
        capability = CapabilityInfo(
            provider="cag",
            node_id=node.node_id,
            confidence=node.similarity_score,  # Basado en embedding similarity
            # ... resto de la capability
        )
        capabilities.append(capability)
    
    return capabilities
```

#### **4. Benefits del approach con RAG:**

✅ **Flexibilidad:** Nuevos nodos automáticamente descubiertos sin mapeos manuales  
✅ **Precisión:** Similarity semántica vs keywords exactas  
✅ **Escalabilidad:** Agregar connectores sin tocar código de discovery  
✅ **Multilenguaje:** Funciona en español/inglés sin mapeos duplicados  
✅ **Contexto:** Considera descripciones completas, no solo nombres  

#### **5. Implementación sugerida:**

```sql
-- Agregar columna de embeddings a tabla existente
ALTER TABLE nodes ADD COLUMN embedding vector(1536);

-- Índice para búsqueda rápida de similaridad
CREATE INDEX idx_nodes_embedding ON nodes USING ivfflat (embedding vector_cosine_ops);
```

```python
# Servicio de embeddings
class EmbeddingService:
    async def generate_node_embeddings(self):
        """Genera embeddings para todos los nodos existentes"""
        nodes = await self.node_repository.get_all()
        for node in nodes:
            text = self._create_searchable_text(node)
            embedding = await self.openai_client.create_embedding(text)
            await self.node_repository.update_embedding(node.id, embedding)
    
    def _create_searchable_text(self, node):
        """Crea texto searchable del nodo"""
        parts = [node.name, node.description]
        
        # Agregar descripciones de acciones
        for action in node.actions:
            parts.extend([action.name, action.description])
        
        # Agregar contexto de parámetros
        for param in node.parameters:
            parts.extend([param.name, param.description])
        
        return " ".join(filter(None, parts))
```

### 🎯 **MIGRACIÓN SUGERIDA:**

1. **Fase 1:** Implementar EmbeddingService y generar embeddings para nodos existentes
2. **Fase 2:** Refactorizar CAGDiscoveryProvider para usar embeddings
3. **Fase 3:** Refactorizar UniversalDiscoveryProvider para eliminar mapeos estáticos
4. **Fase 4:** Deprecar mapeos hardcodeados y NodeSelectionService tradicional

### 📅 **TIMELINE ESTIMADO:**
- **Preparación:** 1 semana (EmbeddingService + DB schema)
- **Implementación:** 2 semanas (Refactoring discovery providers)
- **Testing:** 1 semana (Validar accuracy vs approach actual)
- **Migration:** 1 semana (Deploy + rollback plan)

**Total: ~5 semanas para eliminar mapeos estáticos completamente**

---

*Nota: Esta mejora mantendrá backward compatibility durante la transición y permitirá un sistema de discovery mucho más inteligente y escalable.*