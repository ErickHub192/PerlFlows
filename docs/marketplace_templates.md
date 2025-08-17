# 🏪 Marketplace Templates - Ecosistema de Agentes Verticales

## 📋 Descripción General

El **Marketplace de Templates** permite a los usuarios descubrir, instalar y usar agentes AI especializados en diferentes industrias y casos de uso. Es el "App Store" de agentes AI de Kyra.

## 🏗️ Arquitectura

### **Componentes Principales**

```
Marketplace Ecosystem
├── 📦 Template Storage (JSON + Database)
├── 🔍 Discovery & Search 
├── 📊 Analytics & Usage Tracking
├── 🚀 One-Click Installation
└── 📱 Multi-Channel Deployment
```

### **Template Categories**

- **🇲🇽 Mexico/LATAM**: SAT, compliance fiscal, negocios mexicanos
- **💼 Business & Sales**: CRM, lead generation, sales automation  
- **💰 Finance & Accounting**: Contabilidad, reportes, facturación
- **🎧 Customer Service**: Soporte, tickets, help desk
- **📈 Marketing & Content**: Campaigns, social media, content creation
- **🛒 E-commerce & Retail**: Inventario, órdenes, customer support
- **⚙️ Development & DevOps**: CI/CD, monitoring, deployment automation

## 🎯 Featured Templates

### **🇲🇽 Asistente de Negocio Mexicano** - $79/month
```json
{
  "tools": ["sat_descarga_cfdi", "gmail_send_message", "sheets_read_write", "reflect"],
  "use_cases": [
    "Automatización de descarga de facturas SAT",
    "Generación de reportes fiscales mensuales", 
    "Recordatorios de deadlines fiscales"
  ],
  "target_audience": "PYMES mexicanas, contadores, empresarios"
}
```

### **💼 AI Sales Representative** - $49/month
```json
{
  "tools": ["salesforce_create_lead", "gmail_send_message", "calendar_create_event", "reflect"],
  "use_cases": [
    "Calificación automática de leads",
    "Seguimiento personalizado de prospectos",
    "Programación de demos y reuniones"
  ],
  "target_audience": "Empresas B2B, startups, equipos de ventas"
}
```

### **🎧 Customer Support AI** - $39/month
```json
{
  "tools": ["slack_send_message", "gmail_send_message", "telegram_send_message", "reflect"],
  "use_cases": [
    "Resolución de tickets de soporte",
    "Manejo de consultas frecuentes",
    "Escalación inteligente de casos complejos"
  ],
  "target_audience": "Empresas SaaS, e-commerce, servicios digitales"
}
```

## 🚀 API Endpoints

### **Template Discovery**

```bash
# List all templates
GET /api/marketplace/templates

# Filter by category
GET /api/marketplace/templates?category=mexico_latam

# Filter by tags  
GET /api/marketplace/templates?tags=sat,mexico

# Search templates
GET /api/marketplace/templates?search=contabilidad

# Get specific template
GET /api/marketplace/templates/{template_id}

# List categories
GET /api/marketplace/categories
```

### **Template Installation**

```bash
# Install template as workflow
POST /api/marketplace/install
{
  "template_id": "uuid"
}
```

## 💾 Database Schema

### **Enhanced MarketplaceTemplate Model**

```sql
CREATE TABLE marketplace_templates (
    template_id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    category templatecategory NOT NULL,
    description TEXT,
    spec_json JSONB NOT NULL,
    tags VARCHAR[],
    price_usd INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### **Template Categories Enum**

```sql
CREATE TYPE templatecategory AS ENUM (
    'business_sales',
    'finance_accounting',
    'customer_service', 
    'marketing_content',
    'ecommerce_retail',
    'mexico_latam',
    'development_devops'
);
```

## 📝 Template Specification Format

### **Template JSON Structure**

```json
{
  "template_id": "unique-template-id",
  "name": "Template Name",
  "category": "mexico_latam",
  "price_usd": 7900,
  "description": "Template description",
  "tags": ["tag1", "tag2"],
  "tools": ["tool1", "tool2", "reflect"],
  "instructions": "Agent instructions...",
  "deployment_channels": ["telegram", "web_embed", "whatsapp"],
  "memory_enabled": true,
  "max_iterations": 15,
  "use_cases": ["Use case 1", "Use case 2"],
  "target_audience": "Target market",
  "setup_instructions": "Setup guide",
  "example_prompts": ["Example 1", "Example 2"]
}
```

### **Required Fields**
- `template_id`: Unique identifier
- `name`: Display name
- `category`: Template category enum
- `tools`: Array of required tools
- `instructions`: Agent behavior instructions

### **Optional Fields**
- `price_usd`: Price in cents (default: 0)
- `tags`: Search/filter tags
- `deployment_channels`: Supported channels
- `use_cases`: Business use cases
- `target_audience`: Target market
- `example_prompts`: Example user inputs

## 🔧 Template Management

### **Seeding Templates**

```bash
# Run seed script
python scripts/seed_marketplace_templates.py
```

### **Template Validation**

Templates are validated on installation:
1. **JSON Schema**: Valid template structure
2. **Tools Availability**: All referenced tools exist
3. **Instructions**: Non-empty agent instructions
4. **Deployment**: Valid deployment channels

### **Usage Analytics**

- **usage_count**: Incremented on each install
- **Popular templates**: Sorted by usage_count
- **Category analytics**: Usage by category
- **Search analytics**: Popular search terms

## 🎨 Frontend Integration

### **Enhanced Marketplace UI**

The existing `MarketplacePage.jsx` automatically supports:
- ✅ Category filtering
- ✅ Tag-based filtering  
- ✅ Search functionality
- ✅ Template details view
- ✅ One-click installation

### **New Features Added**
- 🔍 Advanced search with keywords
- 🏷️ Tag-based filtering
- 📊 Usage count display
- 💰 Pricing information
- 🎯 Use cases preview

## 📈 Business Model

### **Pricing Tiers**

```
🆓 Free Templates: $0
├── Basic functionality
└── Essential tools

💎 Premium Templates: $29-99/month
├── Advanced features
├── Multiple tool integrations
└── Industry-specific optimizations

🏢 Enterprise Templates: $299+/month
├── Complex workflows
├── Custom integrations
└── White-label options
```

### **Revenue Sharing**
- **Platform Fee**: 30% on paid templates
- **Creator Revenue**: 70% to template creators
- **Free Templates**: Freemium conversion strategy

## 🚀 Deployment Workflow

### **User Journey**

1. **Discover**: Browse marketplace by category/search
2. **Preview**: View template details, use cases, pricing
3. **Install**: One-click installation as workflow
4. **Configure**: Add credentials for required tools
5. **Deploy**: Choose deployment channel (Telegram, web, etc.)
6. **Use**: Start interacting with specialized agent

### **Installation Process**

```python
# 1. Template validation
await validator.validate_flow_spec(template.spec_json)

# 2. Create workflow from template
flow = await repo.create_flow(template.name, user_id, template.spec_json)

# 3. Track usage
await repo.increment_usage_count(template_id)

# 4. Ready for deployment
return flow
```

## 🔮 Future Enhancements

### **Planned Features**
1. **Template Versioning**: Multiple versions per template
2. **User Reviews**: Ratings and feedback system  
3. **Template Builder**: Visual template creation tool
4. **Community Templates**: User-generated content
5. **Template Dependencies**: Composite templates
6. **A/B Testing**: Template performance optimization

### **Advanced Analytics**
1. **Conversion Tracking**: Install → active usage
2. **Performance Metrics**: Agent success rates
3. **User Retention**: Template stickiness
4. **Revenue Analytics**: Template profitability

## 📞 Support

### **Template Issues**
- **Installation Problems**: Check tool availability and credentials
- **Agent Behavior**: Review template instructions and tools
- **Performance**: Monitor agent memory and iterations

### **Development**
- **Adding Templates**: Place JSON in `/templates/` directory
- **Testing**: Run `pytest tests/marketplace/`
- **Seeding**: Use `scripts/seed_marketplace_templates.py`

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-06  
**Maintainer**: Kyra AI Team