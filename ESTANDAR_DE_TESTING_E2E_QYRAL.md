# 📋 ESTÁNDAR DE TESTING END-TO-END - QYRAL WORKFLOW SYSTEM
**Versión**: 1.0  
**Fecha**: 2025-08-08  
**Autor**: Claude Code Assistant

---

## 🎯 METODOLOGÍA ESTABLECIDA

### **ESTRUCTURA DE TESTING**
Cada flujo de testing se divide en **CICLOS** bien definidos:

1. **CICLO 1**: Primera llamada → SmartForms
2. **CICLO 2**: SmartForms completion → Workflow ready
3. **CICLO 3**: Workflow execution (Runner)
4. **CICLO 4**: Workflow save/update
5. **CICLO 5**: Workflow activation/deactivation

### **PASOS ESTÁNDAR POR CICLO**

#### **PRE-TESTING**
```bash
1. Ejecutar ./clear_logs.sh
2. Crear archivo documentación en carpeta organizada:
   - E2E: `/testing/e2e/{feature}_e2e_2025-{MM-DD}.md`
   - Feature: `/testing/features/{feature}_testing_2025-{MM-DD}.md`
   - Reports: `/testing/reports/{type}_report_2025-{MM-DD}.md`
3. Setup TodoWrite con tareas específicas del ciclo
```

#### **DURING TESTING**  
```bash
1. Usuario ejecuta acción en frontend
2. Monitorear logs en tiempo real
3. Capturar traza completa del flujo
```

#### **POST-TESTING ANALYSIS**
```bash
1. Revisar logs: qyral_app_*.log, frontend.log, errors_*.log
2. Documentar REQUEST TRACE completo
3. Verificar DATA PERSISTENCE ANALYSIS
4. Confirmar CONTEXT CONTINUITY CHECK
5. Validation de PUNTOS CRÍTICOS
6. ERROR HANDLING VERIFICATION
7. Performance metrics
```

---

## 📊 TEMPLATE ESTÁNDAR DE DOCUMENTACIÓN

### **Estructura de Archivo de Análisis**:

```markdown
## 🎯 CICLO X: {DESCRIPCIÓN}
*Status: ✅ [ANÁLISIS COMPLETO]*

### REQUEST TRACE:
```
[TIMESTAMP] ACTION: {descripción}
→ [ENDPOINT] {detalles}
→ [SERVICE] {procesamiento}
→ [DATABASE] {operaciones}
→ [RESPONSE] {resultado}
```

### DATA PERSISTENCE ANALYSIS:
```
BEFORE: {estado inicial}
DURING: 
- ✅ {operación 1}
- ✅ {operación 2}
AFTER: ✅ {estado final}
```

### CONTEXT CONTINUITY CHECK:
```
Input: {contexto recibido}
→ Processing: {cómo se procesa}
→ Output: {resultado context}
→ Verification: {validación}
```

### PUNTOS CRÍTICOS VERIFICADOS:
- ✅ **{Criterio 1}**: {resultado}
- ✅ **{Criterio 2}**: {resultado}
- ⚠️ **{Observación}**: {detalle}

### ERROR HANDLING VERIFICATION:
```
Expected Errors: {errores esperados}
Actual Errors: {errores encontrados}
Fallback Execution: {recuperación}
```

### PERFORMANCE METRICS:
```
Total Time: {tiempo total}
- {Operación 1}: {tiempo}
- {Operación 2}: {tiempo}
```
```

---

## 🧪 CASOS DE TESTING ESPECÍFICOS

### **CASO: WORKFLOW SAVE/UPDATE**
**Pauta de Testing**:
1. **Guardado inicial**: Ejecutar save workflow → Verificar BD entry
2. **Modificación**: Cambiar workflow vía LLM
3. **Re-guardado**: Ejecutar save again → Verificar UPDATE en BD (no INSERT nuevo)

**Comportamiento Esperado**:
- Primera vez: `INSERT INTO flows` 
- Segunda vez: `UPDATE flows SET ... WHERE flow_id = {existing_id}`
- Context preservation entre saves
- No duplicados en database

### **CASO: WORKFLOW ACTIVATION/DEACTIVATION**  
**Pauta de Testing**:
1. Guardar workflow
2. Activar workflow → Verificar `is_active = true`
3. Desactivar workflow → Verificar `is_active = false` 

### **CASO: CONTEXT PRESERVATION**
**Puntos Críticos Siempre Verificar**:
- [ ] UUIDs consistency (Node/Action IDs preserved)
- [ ] WorkflowContextService API response formato correcto
- [ ] SmartForms trigger/completion logic
- [ ] Database persistence sin foreign key violations  
- [ ] Error handling con fallbacks exitosos

---

## 🔧 HERRAMIENTAS Y COMANDOS

### **Scripts Estándar**:
```bash
# Limpiar logs
./clear_logs.sh

# Monitorear logs en vivo
tail -f logs/qyral_app_*.log

# Buscar patrones específicos  
grep -n "PATTERN" logs/qyral_app_*.log
```

### **TodoWrite Structure**:
```javascript
[
  {"content": "Limpiar logs para testing", "status": "in_progress", "priority": "high"},
  {"content": "Análizar flujo [FEATURE] end-to-end", "status": "pending", "priority": "high"},  
  {"content": "Documentar traza completa", "status": "pending", "priority": "medium"},
  {"content": "Verificar datos persistidos", "status": "pending", "priority": "medium"},
  {"content": "Generar reporte final", "status": "pending", "priority": "low"}
]
```

---

## 🎯 SUCCESS CRITERIA ESTÁNDAR

### **Funcionalidad**:
- ✅ Context preservation 100%
- ✅ Database operations correctas
- ✅ Error recovery automático  
- ✅ Frontend feedback apropiado

### **Performance**:
- ✅ Response times < 10s para operaciones normales
- ✅ Database queries optimizadas  
- ✅ Memory usage estable

### **Arquitectura**:
- ✅ No parsing frágil usado
- ✅ API-first approach confirmado
- ✅ WorkflowContextService como single source of truth

---

## 📝 NOTAS DE IMPLEMENTACIÓN

### **Comandos para Futuras Sesiones**:
```
"Lee el estándar de testing E2E y aplica la metodología completa para [FEATURE]"
```

### **Archivos de Referencia**:
- `/testing/e2e/end_to_end_analysis_2025-08-08.md` - Ejemplo completo de 3 ciclos
- `tumamajajaja.txt` - Context del refactor WorkflowContextService
- `/testing/README.md` - Estructura de carpetas testing
- Este archivo - Metodología estandarizada

### **Key Learnings**:
1. **Siempre limpiar logs primero** - Critical para analysis limpio
2. **TodoWrite proactivo** - Tracking es esencial para completitud  
3. **Documentar en tiempo real** - No batch updates
4. **Focus en puntos críticos** - Context, performance, database ops
5. **Reportes concisos pero completos** - Usuario necesita summary ejecutivo
6. **Organizar archivos testing** - Usar `/testing/` estructura para orden

---

*Última actualización: 2025-08-08*  
*Probado exitosamente en: WorkflowContextService refactor testing*