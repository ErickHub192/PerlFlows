# Code Executor - Ejemplos de Uso para Workflows

El Code Executor Handler permite ejecutar código Python en workflows de Kyra, similar al nodo de código de n8n.

## Casos de Uso Comunes

### 1. Formatear Datos de Google Sheets

```python
# input_data contiene los datos del sheet
formatted_rows = []

for row in input_data.get('values', []):
    if len(row) >= 3:  # Asegurar que tenga suficientes columnas
        formatted_rows.append({
            'cliente': row[0].strip().title(),
            'email': row[1].strip().lower(),
            'monto': round(float(row[2].replace('$', '').replace(',', '')), 2),
            'fecha_formateada': datetime.datetime.strptime(row[3], '%d/%m/%Y').strftime('%Y-%m-%d')
        })

result = {
    'total_registros': len(formatted_rows),
    'datos_formateados': formatted_rows
}
```

### 2. Procesar Respuesta de API

```python
# input_data es la respuesta de una API REST
import json

processed_data = []

for item in input_data.get('data', []):
    # Limpiar y formatear cada item
    clean_item = {
        'id': item['id'],
        'name': item['name'].strip(),
        'status': 'activo' if item.get('active', False) else 'inactivo',
        'created_at': item['created_at'][:10],  # Solo fecha, sin hora
        'metadata': {
            'source': 'api_externa',
            'processed_at': datetime.datetime.now().isoformat()
        }
    }
    
    # Solo incluir items válidos
    if clean_item['name'] and clean_item['id']:
        processed_data.append(clean_item)

# Preparar para el siguiente nodo
result = {
    'items': processed_data,
    'summary': {
        'total_processed': len(processed_data),
        'total_received': len(input_data.get('data', [])),
        'success_rate': len(processed_data) / len(input_data.get('data', [1])) * 100
    }
}
```

### 3. Cálculos Financieros

```python
# input_data contiene transacciones financieras
transactions = input_data.get('transactions', [])

total_ingresos = 0
total_gastos = 0
categorias = {}

for transaction in transactions:
    amount = float(transaction['amount'])
    category = transaction.get('category', 'otros')
    
    if amount > 0:
        total_ingresos += amount
    else:
        total_gastos += abs(amount)
    
    # Agrupar por categoría
    if category not in categorias:
        categorias[category] = {'total': 0, 'count': 0}
    
    categorias[category]['total'] += abs(amount)
    categorias[category]['count'] += 1

# Calcular métricas
balance = total_ingresos - total_gastos
categoria_mayor_gasto = max(categorias.items(), key=lambda x: x[1]['total'])

result = {
    'resumen_financiero': {
        'ingresos_totales': round(total_ingresos, 2),
        'gastos_totales': round(total_gastos, 2),
        'balance': round(balance, 2),
        'categoria_mayor_gasto': {
            'nombre': categoria_mayor_gasto[0],
            'monto': round(categoria_mayor_gasto[1]['total'], 2)
        }
    },
    'categorias_detalle': {k: {'total': round(v['total'], 2), 'count': v['count']} 
                          for k, v in categorias.items()},
    'alertas': [
        'Balance negativo' if balance < 0 else 'Balance positivo',
        f'Mayor gasto en: {categoria_mayor_gasto[0]}'
    ]
}
```

### 4. Validación y Limpieza de Datos

```python
# input_data contiene una lista de contactos para validar
import re

email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
phone_pattern = re.compile(r'^[\+]?[\d\s\-\(\)]{10,}$')

valid_contacts = []
invalid_contacts = []

for contact in input_data.get('contacts', []):
    errors = []
    
    # Validar email
    email = contact.get('email', '').strip()
    if not email:
        errors.append('Email requerido')
    elif not email_pattern.match(email):
        errors.append('Email inválido')
    
    # Validar teléfono
    phone = contact.get('phone', '').strip()
    if phone and not phone_pattern.match(phone):
        errors.append('Teléfono inválido')
    
    # Validar nombre
    name = contact.get('name', '').strip()
    if not name or len(name) < 2:
        errors.append('Nombre requerido (mínimo 2 caracteres)')
    
    contact_clean = {
        'name': name.title() if name else '',
        'email': email.lower() if email else '',
        'phone': re.sub(r'[\s\-\(\)]', '', phone) if phone else '',
        'company': contact.get('company', '').strip(),
        'errors': errors
    }
    
    if not errors:
        valid_contacts.append(contact_clean)
    else:
        invalid_contacts.append(contact_clean)

result = {
    'contactos_validos': valid_contacts,
    'contactos_invalidos': invalid_contacts,
    'estadisticas': {
        'total_procesados': len(input_data.get('contacts', [])),
        'validos': len(valid_contacts),
        'invalidos': len(invalid_contacts),
        'tasa_exito': round(len(valid_contacts) / len(input_data.get('contacts', [1])) * 100, 2)
    }
}
```

### 5. Generación de Reportes

```python
# input_data contiene datos de ventas para generar reporte
import datetime

ventas = input_data.get('ventas', [])
fecha_reporte = datetime.datetime.now()

# Agrupar por vendedor
vendedores = {}
for venta in ventas:
    vendedor = venta.get('vendedor', 'Sin asignar')
    if vendedor not in vendedores:
        vendedores[vendedor] = {
            'total_ventas': 0,
            'numero_ventas': 0,
            'productos_vendidos': set()
        }
    
    vendedores[vendedor]['total_ventas'] += float(venta.get('monto', 0))
    vendedores[vendedor]['numero_ventas'] += 1
    vendedores[vendedor]['productos_vendidos'].add(venta.get('producto', ''))

# Preparar reporte
reporte = {
    'metadata': {
        'fecha_generacion': fecha_reporte.strftime('%Y-%m-%d %H:%M:%S'),
        'periodo': input_data.get('periodo', 'No especificado'),
        'total_registros': len(ventas)
    },
    'resumen_general': {
        'total_ventas': sum(v['total_ventas'] for v in vendedores.values()),
        'numero_vendedores': len(vendedores),
        'venta_promedio': sum(v['total_ventas'] for v in vendedores.values()) / len(vendedores) if vendedores else 0
    },
    'ranking_vendedores': sorted([
        {
            'vendedor': k,
            'total_ventas': round(v['total_ventas'], 2),
            'numero_ventas': v['numero_ventas'],
            'venta_promedio': round(v['total_ventas'] / v['numero_ventas'], 2) if v['numero_ventas'] > 0 else 0,
            'productos_unicos': len(v['productos_vendidos'])
        } for k, v in vendedores.items()
    ], key=lambda x: x['total_ventas'], reverse=True)
}

result = reporte
```

### 6. Integración con APIs - Preparar Payload

```python
# input_data contiene datos del usuario que queremos enviar a CRM
user_data = input_data

# Mapear campos internos a campos del CRM externo
crm_payload = {
    'contact': {
        'firstName': user_data.get('nombre', '').split()[0] if user_data.get('nombre') else '',
        'lastName': ' '.join(user_data.get('nombre', '').split()[1:]) if len(user_data.get('nombre', '').split()) > 1 else '',
        'email': user_data.get('email', ''),
        'phone': user_data.get('telefono', ''),
        'company': user_data.get('empresa', ''),
        'customFields': {
            'source': 'kyra_workflow',
            'created_date': datetime.datetime.now().isoformat(),
            'lead_score': user_data.get('puntuacion', 0),
            'interests': ','.join(user_data.get('intereses', []))
        }
    },
    'tags': [
        'kyra_import',
        user_data.get('segmento', 'general'),
        f"score_{user_data.get('puntuacion', 0)//10*10}"  # Score bands: 0-10, 10-20, etc.
    ],
    'pipeline': {
        'stage': 'new_lead' if user_data.get('puntuacion', 0) < 50 else 'qualified_lead'
    }
}

# Limpiar campos vacíos
def clean_empty_fields(obj):
    if isinstance(obj, dict):
        return {k: clean_empty_fields(v) for k, v in obj.items() if v not in ['', None, [], {}]}
    elif isinstance(obj, list):
        return [clean_empty_fields(item) for item in obj if item not in ['', None]]
    return obj

result = clean_empty_fields(crm_payload)
```

## Configuración en Workflows

### Parámetros del Nodo Code:

```json
{
  "node_type": "Code.execute",
  "parameters": {
    "code": "# Tu código aquí",
    "input_data": "{{ $previous.data }}",
    "variables": {
      "api_key": "{{ $credentials.api_key }}",
      "base_url": "https://api.ejemplo.com"
    },
    "return_variable": "result",
    "timeout": 30
  }
}
```

### Acceso a Datos Anteriores:

- `input_data`: Datos del nodo anterior
- `variables`: Variables personalizadas
- Resultado se guarda en la variable especificada en `return_variable`

### Bibliotecas Disponibles:

- **Básicas**: json, math, datetime, time, random, re, collections
- **Datos**: pandas (si está instalado), numpy
- **Web**: requests (para llamadas HTTP adicionales)
- **Texto**: string, textwrap, unicodedata

## Mejores Prácticas

1. **Siempre validar input_data**:
   ```python
   if not input_data or not isinstance(input_data, dict):
       result = {"error": "Invalid input data"}
   ```

2. **Manejar errores graciosamente**:
   ```python
   try:
       # Tu lógica aquí
       result = processed_data
   except Exception as e:
       result = {"error": str(e), "original_data": input_data}
   ```

3. **Documentar el código**:
   ```python
   # Este código formatea datos de ventas para el dashboard
   # Input: lista de transacciones
   # Output: métricas agregadas por vendedor
   ```

4. **Usar return_variable apropiado**:
   - `result`: Para datos procesados
   - `formatted_data`: Para datos transformados
   - `metrics`: Para cálculos y estadísticas