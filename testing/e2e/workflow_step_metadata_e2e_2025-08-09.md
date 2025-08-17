# 📋 E2E TESTING - WORKFLOW STEP METADATA ISSUES
**Feature**: Workflow Step Metadata Persistence  
**Fecha**: 2025-08-09  
**Issue**: step_number se pierde (nulo) y params_meta se vacía al guardar workflows  
**Autor**: Claude Code Assistant

## 🔧 CAMBIOS APLICADOS (BACKUP POINT):

### CAMBIO 1: Bug execution_step y params_meta (ARREGLADO)
**Archivo**: `/mnt/c/kyraProyecto/app/workflow_engine/llm/llm_workflow_planner.py`
**Líneas**: 1538, 1320, 1558, 1340

**Cambio**:
```python
# ANTES (BUGGY):
"execution_step": step.get("step"),
"params_meta": step.get("params_meta", []),

# DESPUÉS (FIXED):
"execution_step": step.get("execution_step") or step.get("step"),
"params_meta": step.get("params_meta", []) or (action_metadata.get("parameters", []) if action_metadata else []),
```

### CAMBIO 2: Bug StepMetaDTO conversion (ARREGLADO)
**Archivo**: `/mnt/c/kyraProyecto/app/services/conversation_memory_service.py`
**Líneas**: 170, 325

**Cambio**:
```python
# ANTES (BUGGY):
steps=step_dtos,

# DESPUÉS (FIXED):
steps=[step.model_dump() if hasattr(step, 'model_dump') else step for step in step_dtos],
```

### CAMBIO 3: Previous workflow metadata preservation (NUEVO - CONSERVADOR)
**Archivo**: `/mnt/c/kyraProyecto/app/workflow_engine/core/workflow_engine_simple.py`
**Líneas**: 478-487

**Cambio**:
```python
# ANTES:
complete_workflow_context = {
    "steps": planned_steps,
    # ... solo campos básicos
}

# DESPUÉS (MINIMAL FIX):
complete_workflow_context = workflow_context.copy() if workflow_context else {}
complete_workflow_context.update({
    "steps": planned_steps,  # ✅ UPDATED STEPS with latest metadata
    # ... campos actualizados
})
```

### ROLLBACK INSTRUCTIONS:
Si algo se rompe, revertir estos 3 cambios en orden inverso:
1. Revertir `workflow_engine_simple.py` línea 478-487
2. Revertir `conversation_memory_service.py` líneas 170, 325  
3. Revertir `llm_workflow_planner.py` líneas 1538, 1320, 1558, 1340

---

## 🚨 PROBLEMAS IDENTIFICADOS

### **PROBLEMA 1**: Pérdida de step_number
- **Síntoma**: `execution_step` se guarda como `null` en DB
- **Impacto**: Workflows no mantienen orden de ejecución
- **Estado**: 🔍 Investigando

### **PROBLEMA 2**: Pérdida de params_meta  
- **Síntoma**: `params_meta` se vacía `[]` al guardar
- **Impacto**: Falta información de validación de parámetros
- **Estado**: 🔍 Investigando

### **PROBLEMA 3**: Metadata excesiva
- **Síntoma**: Demasiada metadata vs ejemplo 1 en xs.txt
- **Comparación**: xs.txt ejemplo 1 (simple) vs ejemplo 2 (refactor con exceso)
- **Estado**: 🔍 Investigando

---

## 📊 COMPARACIÓN DE METADATA (xs.txt)

### **EJEMPLO 1 - METADATA SIMPLE (PRE-REFACTOR)**
```json
{
  "execution_step": 1,              ✅ PRESENT
  "params_meta": [                  ✅ COMPLETE
    {
      "name": "cron_expression",
      "type": "string", 
      "param_id": "114f20a2-...",
      "required": true,
      "description": "Expresión CRON"
    }
  ],
  "step_metadata": {
    "planned_by": "kyra",
    "inferred_parameters": 1,
    "selection_reasoning": ""
  }
}
```

### **EJEMPLO 2 - METADATA EXCESIVA (POST-REFACTOR)**
```json
{
  "execution_step": null,           ❌ LOST!
  "params_meta": [],                ❌ EMPTY!
  "parameters_metadata": [...],     ❓ DUPLICATED?
  "step_metadata": {...},           ✅ PRESENT
  "kyra_confidence": 0.8,          ❓ NECESSARY?
  // + otros campos adicionales
}
```

---

## 🔧 TESTING CYCLES

### **CICLO 1**: Workflow Creation → SmartForms
- [ ] Usuario crea workflow en frontend
- [ ] Monitor logs durante creación
- [ ] Verificar metadata inicial

### **CICLO 2**: SmartForms Completion → Ready
- [ ] Usuario completa SmartForms  
- [ ] Monitor logs durante completion
- [ ] Verificar preservación de metadata

### **CICLO 3**: Workflow Save/Update
- [ ] Sistema guarda workflow en DB
- [ ] Monitor logs durante guardado
- [ ] **PUNTO CRÍTICO**: ¿Dónde se pierden step_number y params_meta?

---

## 🚨 CICLO 1 ANALYSIS - PROBLEMAS ENCONTRADOS

### **PROBLEMA 1 CONFIRMADO**: execution_step = NULL
```json
{
  "id": "8cbf8373-d888-45cc-bea1-0a1cae992df0",
  "execution_step": null,  ❌ SIEMPRE NULL DESDE EL INICIO
  // ...
}
```

### **PROBLEMA 2 CONFIRMADO**: params_meta = [] (VACÍO)
```json
{
  "params_meta": [],  ❌ SIEMPRE VACÍO DESDE EL INICIO  
  "parameters_metadata": [],  ❌ TAMBIÉN VACÍO
  // ...
}
```

### **PROBLEMA 3 CONFIRMADO**: Metadata duplicada/innecesaria
```json
{
  "params": {...},           // DUPLICADO
  "parameters": {...},       // DUPLICADO  
  "params_meta": [],         // VACÍO
  "parameters_metadata": [], // VACÍO (DUPLICADO)
  "kyra_confidence": 0.8,    // ¿NECESARIO?
}
```

### **ROOT CAUSE IDENTIFICADO**:
El workflow engine está generando los steps **SIN** asignar:
1. `execution_step` (step ordering)
2. `params_meta` (parameter metadata)

**Comparación con xs.txt ejemplo 1**:
- ✅ ANTES: `execution_step: 1`, `params_meta: [...]`
- ❌ AHORA: `execution_step: null`, `params_meta: []`

---

## 📝 LOG ANALYSIS TEMPLATE

### **REQUEST TRACE**
```
[TIMESTAMP] REQUEST: /api/workflows/create
[TIMESTAMP] LLM PLANNING: step_metadata generated
[TIMESTAMP] PARAMS VALIDATION: params_meta populated
[TIMESTAMP] DB SAVE: step_number assigned
[TIMESTAMP] DB RESULT: ❌ step_number=NULL, params_meta=[]
```

### **DATA PERSISTENCE ANALYSIS**
- ✅ **Workflow spec**: Guardado correctamente
- ❌ **Step execution_step**: Se pierde → NULL
- ❌ **Step params_meta**: Se vacía → []
- ❓ **Metadata duplicada**: parameters_metadata vs params_meta

### **CONTEXT CONTINUITY CHECK**  
- ✅ **Workflow ID**: Preservado
- ✅ **Step IDs**: Preservados
- ❌ **Step order**: Perdido (execution_step=NULL)
- ❌ **Param validation**: Perdida (params_meta=[])

---

## 🎯 PUNTOS CRÍTICOS A MONITOREAR

1. **WorkflowEngine.process_user_request()**
   - ¿Se genera execution_step correctamente?
   - ¿params_meta está poblado al crear steps?

2. **Workflow Save/Update Service**
   - ¿Qué servicio guarda en DB?
   - ¿Se mapean correctamente los campos?

3. **Step Serialization**
   - ¿Se serializa execution_step?
   - ¿Se preserva params_meta?

4. **Database Schema**
   - ¿Campos execution_step y params_meta existen en schema?
   - ¿Hay restricciones que causan NULL/[]?

---

## 📊 EXPECTED vs ACTUAL

### **EXPECTED** (Ejemplo 1 xs.txt):
```json
{
  "execution_step": 1,
  "params_meta": [{"name": "...", "type": "...", ...}]
}
```

### **ACTUAL** (Ejemplo 2 xs.txt):
```json
{
  "execution_step": null,
  "params_meta": []
}
```

### **DIFFERENCE**: 
- ❌ execution_step: 1 → null
- ❌ params_meta: [objects] → []

---

## 🔍 INVESTIGATION TODOS

- [ ] **CICLO 1**: Crear workflow y monitorear logs
- [ ] **CICLO 2**: Completar SmartForms y monitorear logs  
- [ ] **CICLO 3**: Análisis de logs de guardado en DB
- [ ] **ANALYSIS**: Identificar punto exacto donde se pierden datos
- [ ] **FIX**: Implementar corrección
- [ ] **VERIFY**: Confirmar que metadata se preserva correctamente

---

## 📋 LOG FILES TO MONITOR

- `logs/qyral_app_*.log` - Main application logs
- `logs/frontend.log` - Frontend interaction logs
- `logs/errors_*.log` - Error logs
- Database query logs (if available)

---

## ✅ BUGS IDENTIFICADOS Y ARREGLADOS

### **BUG 1 ARREGLADO**: execution_step field mapping
**Ubicación**: `/app/workflow_engine/llm/llm_workflow_planner.py`
**Líneas**: 1320, 1538

**ANTES**:
```python
"execution_step": step.get("step"),  # ❌ Campo incorrecto
```

**DESPUÉS**:  
```python
"execution_step": step.get("execution_step"),  # ✅ Campo correcto
```

### **BUG 2 ARREGLADO**: params_meta priority
**Ubicación**: `/app/workflow_engine/llm/llm_workflow_planner.py` 
**Línea**: 1543

**ANTES**:
```python
"params_meta": action_metadata.get("parameters", []) if action_metadata else [],
```

**DESPUÉS**:
```python  
"params_meta": step.get("params_meta", []) or (action_metadata.get("parameters", []) if action_metadata else []),
```

### **ROOT CAUSE CONFIRMED**:
- ✅ **LLM genera correctamente**: `execution_step: 1, 2` en RAW STEP DATA
- ✅ **Memoria preserva**: execution_step se guardaba correctamente  
- ❌ **Bug en mapeo**: `step.get("step")` en vez de `step.get("execution_step")`
- ❌ **params_meta perdido**: No priorizaba datos del step original

### **EXPECTED RESULT**:
Después de este fix, los workflows deberían mantener:
- `execution_step: 1, 2, 3...` ✅
- `params_meta: [metadata objects]` ✅ (si el LLM los genera)

---

*Testing iniciado: 2025-08-09*  
*Status: ✅ BUGS ARREGLADOS - Ready for verification*
*Next: Test workflow creation to verify fixes*