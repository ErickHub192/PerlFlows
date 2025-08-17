# 📦 Templates Directory

## 📁 Directory Structure

```
templates/
├── README.md           ← Este archivo
├── seeds/              ← Initial template definitions (JSON)
│   ├── mexican_business_assistant.json
│   ├── ai_sales_rep.json
│   └── customer_support_ai.json
└── examples/           ← Template examples for developers
    └── template_schema.json
```

## 🔄 Template Lifecycle

### **1. Development Phase**
- Crear JSON files en `seeds/` directory
- Definir template specification completa
- Versionar en git para tracking

### **2. Seeding Phase** 
```bash
# Migrar JSONs → Database
python scripts/seed_marketplace_templates.py
```

### **3. Production Phase**
- Templates servidos desde database
- API endpoints usan BD (NO JSON files)
- JSON files **OPCIONALES** después del seed

## ❓ **FAQ**

### **¿Puedo borrar los JSON files después del seed?**
**SÍ!** Una vez que corres el seed script:
- ✅ Templates están en la database
- ✅ API funciona sin JSON files
- ✅ Puedes borrar `seeds/` directory si quieres

### **¿Para qué mantener los JSON files?**
**Opcional**, pero útil para:
- 📝 Version control de templates
- 🔄 Re-seeding en desarrollo
- 📋 Backup/reference de templates originales
- 🚀 Deployment en nuevos environments

### **¿Cómo agregar nuevos templates?**

**Opción A: Via JSON + Seed (Desarrollo)**
```bash
# 1. Crear JSON en seeds/
echo '{"name": "New Template", ...}' > seeds/new_template.json

# 2. Actualizar seed script
# 3. Re-run seed
python scripts/seed_marketplace_templates.py
```

**Opción B: Via Admin API (Producción)**
```bash
# POST direct a database
curl -X POST /api/marketplace/admin/templates \
  -d '{"name": "New Template", ...}'
```

## 🗂️ File Organization

### **Keep for Development:**
- `seeds/*.json` - Para version control y re-seeding
- `README.md` - Documentación

### **Safe to Delete (Post-Seed):**
- `seeds/*.json` - Si ya no necesitas re-seed
- Pero recomendado mantener para backup

## 🎯 **Recommended Workflow**

### **Local Development:**
1. Keep `seeds/` for easy re-seeding
2. Modify JSONs para template changes
3. Re-run seed script durante development

### **Production:**
1. Run seed script ONCE en deployment
2. Manage templates via admin interface
3. `seeds/` directory es opcional

### **Version Control:**
- ✅ Commit `seeds/*.json` para template history
- ✅ Commit `README.md` para documentación
- ❌ NO commit generated database files

## 🚀 **Commands**

```bash
# Seed templates (development)
python scripts/seed_marketplace_templates.py

# Check seeded templates
curl http://localhost:8000/api/marketplace/templates

# Clean seed directory (optional, post-production)
rm -rf templates/seeds/
```