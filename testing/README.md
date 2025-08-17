# 🧪 TESTING DIRECTORY - QYRAL WORKFLOW SYSTEM

## 📁 Estructura de Carpetas

```
testing/
├── e2e/                    # End-to-End Testing
│   ├── workflow_context_service_2025-08-08.md
│   └── [feature]_e2e_2025-{date}.md
├── features/               # Feature Testing Específico  
│   ├── smartforms_testing_2025-{date}.md
│   ├── oauth_flows_testing_2025-{date}.md
│   └── [feature]_test_2025-{date}.md
├── reports/               # Reportes Consolidados
│   ├── weekly_testing_summary_2025-{week}.md
│   └── regression_test_results_2025-{date}.md
└── README.md             # Este archivo
```

## 🎯 Convenciones de Naming

### **E2E Testing**:
- Formato: `{main_feature}_e2e_2025-{MM-DD}.md`
- Ejemplo: `workflow_save_update_e2e_2025-08-08.md`

### **Feature Testing**:
- Formato: `{feature_name}_testing_2025-{MM-DD}.md`  
- Ejemplo: `smartforms_oauth_testing_2025-08-08.md`

### **Reports**:
- Formato: `{type}_report_2025-{MM-DD}.md`
- Ejemplo: `regression_test_report_2025-08-08.md`

## 📋 Files Actuales

- `e2e/end_to_end_analysis_2025-08-08.md` - WorkflowContextService refactor testing (3 ciclos)
- `../ESTANDAR_DE_TESTING_E2E_QYRAL.md` - Metodología completa

## 🔧 Próximos Tests Programados

- [ ] Workflow Save/Update E2E
- [ ] Workflow Activation/Deactivation
- [ ] SmartForms OAuth Integration
- [ ] Error Recovery Testing
- [ ] Performance Regression Testing

---

*Estructura creada: 2025-08-08*  
*Mantenedor: Claude Code Assistant*