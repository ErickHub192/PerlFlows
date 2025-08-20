# PLAN DE REPARACIÓN: CORRUPCIÓN UUID WEBHOOK

## 🔍 ANÁLISIS DEL PROBLEMA

### **Root Cause Identificado:**
En `/mnt/c/kyraProyecto/app/services/conversation_memory_service.py` línea donde se crea StepMetaDTO:

```python
action_id=step.get("action_id", step.get("id")),
```

**Problema:** Si `action_id` no existe en el step, usa `step.get("id")` como fallback. Este `id` puede ser:
1. Un UUID diferente (step ID vs action ID)
2. Un UUID truncado o corrupto
3. No corresponder al verdadero `action_id`

### **Evidencia Específica del Webhook:**
- **UUID Correcto:** `f2fee4b9-9a32-4906-a59d-ad343e7a9e3c`
- **UUID Corrupto:** `f2fee4b9-9a32-4906-a59d-ad343e7a9c` (pierde `e3`)
- Solo afecta nodo Webhook, otros nodos (Drive_Trigger, Gmail) funcionan correctamente
- Error: `invalid group length in group 4: expected 12, found 10`

### **Flujo del Problema:**
1. ✅ LLM genera execution_plan con `action_id` correcto
2. ❌ Durante SmartForm processing, se pierde o corrompe `action_id` 
3. ❌ `conversation_memory_service` usa `step["id"]` corrupto como fallback
4. ❌ StepMetaDTO validation falla por UUID inválido
5. ❌ Nodo se marca como "Unknown_Node"

---

## 🛠️ PLAN DE REPARACIÓN

### **FASE 1: VALIDACIÓN DE DATA INTEGRITY** 
**Prioridad: ALTA | Tiempo: 30 min**

1. **Verificar qué contiene `step["id"]` vs `step["action_id"]`**
   ```python
   # En conversation_memory_service.py, agregar logging exhaustivo:
   logger.info(f"🔍 STEP DEBUG: id={step.get('id')}, action_id={step.get('action_id')}")
   logger.info(f"🔍 STEP DEBUG: id type={type(step.get('id'))}, action_id type={type(step.get('action_id'))}")
   ```

2. **Rastrear dónde se pierde/corrompe action_id**
   - Verificar si `execution_plan` del LLM incluye `action_id`
   - Confirmar si SmartForm processing preserva `action_id`
   - Identificar punto exacto de corrupción

### **FASE 2: FIX INMEDIATO - FALLBACK SEGURO**
**Prioridad: ALTA | Tiempo: 45 min**

3. **Mejorar fallback logic en StepMetaDTO creation**
   ```python
   # Reemplazar:
   action_id=step.get("action_id", step.get("id")),
   
   # Con:
   action_id=self._get_safe_action_id(step),
   ```

4. **Implementar `_get_safe_action_id()` method**
   ```python
   def _get_safe_action_id(self, step):
       """Obtiene action_id seguro, buscando en múltiples fuentes"""
       
       # Prioridad 1: action_id directo
       action_id = step.get("action_id")
       if action_id and self._is_valid_uuid(action_id):
           return action_id
           
       # Prioridad 2: Buscar en xp.txt por node_name
       node_name = step.get("node_name")
       if node_name:
           correct_action_id = self._lookup_action_id_by_node_name(node_name)
           if correct_action_id:
               logger.warning(f"🔧 RECOVERED action_id for {node_name}: {correct_action_id}")
               return correct_action_id
       
       # Prioridad 3: Generar UUID nuevo como último recurso
       logger.error(f"🔧 GENERATING NEW UUID for step: {step}")
       return str(uuid.uuid4())
   ```

### **FASE 3: PREVENCIÓN - WEBHOOK ESPECÍFICO**
**Prioridad: ALTA | Tiempo: 60 min**

5. **Identificar por qué solo Webhook se corrompe**
   - Revisar `webhook_trigger_handler.py` procesamiento especial
   - Verificar si hay template processing específico para webhooks
   - Comparar con `Drive_Trigger` que funciona correctamente

6. **Implementar validación previa para Webhook**
   ```python
   # En llm_workflow_planner.py, agregar webhook validation:
   if step.get("node_name") == "Webhook":
       expected_action_id = "f2fee4b9-9a32-4906-a59d-ad343e7a9e3c"  # From xp.txt
       if step.get("action_id") != expected_action_id:
           logger.warning(f"🔧 WEBHOOK UUID MISMATCH: correcting {step.get('action_id')} -> {expected_action_id}")
           step["action_id"] = expected_action_id
   ```

### **FASE 4: TESTS Y VALIDACIÓN**
**Prioridad: MEDIA | Tiempo: 30 min**

7. **Test cases específicos**
   - Crear workflow Webhook + Gmail desde cero
   - Llenar SmartForm y verificar que UUIDs se preservan
   - Confirmar que StepMetaDTO se crea exitosamente
   - Verificar que otros nodos siguen funcionando

8. **Regression testing**
   - Probar workflows existentes (Drive + Gmail, Cron + Slack)
   - Confirmar que el fix no rompe nodos funcionando

---

## 🎯 IMPLEMENTACIÓN PRIORITARIA

### **QUICK FIX (15 min):**
```python
# En conversation_memory_service.py, línea con StepMetaDTO:
action_id = step.get("action_id")
if not action_id or not self._is_valid_uuid(action_id):
    # WEBHOOK SPECIFIC FIX
    if step.get("node_name") == "Webhook":
        action_id = "f2fee4b9-9a32-4906-a59d-ad343e7a9e3c"  # From xp.txt
        logger.warning(f"🔧 FIXED WEBHOOK UUID: using correct action_id")
    else:
        action_id = step.get("id", str(uuid.uuid4()))

step_dto = StepMetaDTO(
    # ... otros campos
    action_id=action_id,
    # ... resto
)
```

### **VERIFICACIÓN IMMEDIATE:**
1. Reiniciar backend
2. Crear workflow webhook + gmail 
3. Llenar SmartForm
4. Verificar que no aparece error "DIRECT FORCE UPDATE DTO ERROR"
5. Confirmar que node_name="Webhook" (no "Unknown_Node")

---

## 📊 ESTIMACIÓN TOTAL

- **Quick Fix:** 15 min
- **Full Fix:** 2.5 horas
- **Testing:** 30 min
- **TOTAL:** 3 horas

## ✅ SUCCESS CRITERIA

- [ ] Error "DIRECT FORCE UPDATE DTO ERROR" eliminado
- [ ] Webhook node_name="Webhook" (no "Unknown_Node") 
- [ ] UUID webhook preservado: `f2fee4b9-9a32-4906-a59d-ad343e7a9e3c`
- [ ] Otros nodos siguen funcionando normalmente
- [ ] SmartForm processing completado sin errores