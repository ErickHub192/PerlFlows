import { Link } from 'preact-router/match';
import { useState, useEffect } from 'preact/hooks';
import FileDiscoveryModal from '../components/FileDiscoveryModal';

const Dashboard = ({ isAuthenticated = false, onLoginClick = () => {} }) => {
  const [hoveredCard, setHoveredCard] = useState(null);
  const [showAutoDiscovery, setShowAutoDiscovery] = useState(false);
  const [testUserIntent, setTestUserIntent] = useState('Quiero conectar mi Google Sheets para automatizar reportes');

  // Validación defensiva
  if (typeof isAuthenticated !== 'boolean') {
    console.warn('Dashboard: isAuthenticated debe ser boolean, recibido:', typeof isAuthenticated);
  }

  const sections = [
    {
      id: 'marketplace',
      title: 'Marketplace',
      description: 'Plantillas pre-hechas para empezar rápidamente',
      icon: '🛒',
      href: '#',
      requiresAuth: false,
      locked: true,
      features: [
        'Templates listos para usar',
        'Casos de uso populares',
        'Instalación con un click',
        'Ejemplos reales'
      ]
    },
    {
      id: 'agents',
      title: 'AI Agents',
      description: 'Agentes inteligentes para automatización avanzada',
      icon: '🤖',
      href: '#',
      requiresAuth: false,
      locked: true,
      features: [
        'Agentes personalizados',
        'Integración con APIs',
        'Lógica compleja',
        'Ejecución autónoma'
      ]
    },
    {
      id: 'integrations',
      title: 'Integraciones',
      description: 'Catálogo completo de servicios y APIs disponibles',
      icon: '🔌',
      href: '#integrations-section',
      requiresAuth: false,
      features: [
        'Google (Drive, Sheets, Gmail)',
        'GitHub, Slack, Microsoft',
        'Dropbox, Salesforce, Stripe',
        'Code Executor, Webhooks'
      ]
    },
    {
      id: 'settings',
      title: 'Configuración',
      description: 'Credenciales, perfiles y ajustes de cuenta',
      icon: '⚙️',
      href: '#',
      requiresAuth: true,
      features: [
        'Gestión de credenciales',
        'Configuración de cuenta',
        'Métodos de pago',
        'Notificaciones'
      ]
    }
  ];

  const flowSteps = [
    { step: 1, text: 'Describe tu automatización', icon: '💭' },
    { step: 2, text: 'IA procesa y configura', icon: '🧠' },
    { step: 3, text: 'Se ejecuta automáticamente', icon: '⚡' },
    { step: 4, text: 'Monitorea y optimiza', icon: '📈' }
  ];

  const integrationCategories = [
    {
      name: '🌐 Google Workspace',
      items: [
        { name: 'Gmail', actions: 'Enviar mensajes, triggers' },
        { name: 'Google Drive', actions: 'Upload, sincronización' },
        { name: 'Google Sheets', actions: 'Leer/escribir, crear hojas' },
        { name: 'Google Calendar', actions: 'Crear eventos' },
        { name: 'Google Docs', actions: 'Crear documentos' }
      ]
    },
    {
      name: '💼 Productividad',
      items: [
        { name: 'Slack', actions: 'Mensajes, triggers de canales' },
        { name: 'Microsoft Outlook', actions: 'Enviar correos' },
        { name: 'GitHub', actions: 'Crear issues, triggers' },
        { name: 'Airtable', actions: 'Leer/escribir datos' }
      ]
    },
    {
      name: '☁️ Storage & Files',
      items: [
        { name: 'Dropbox', actions: 'Upload archivos' },
        { name: 'Code Executor', actions: 'Ejecutar código Python/JS' },
        { name: 'PostgreSQL', actions: 'Queries personalizadas' },
        { name: 'HTTP Requests', actions: 'APIs personalizadas' }
      ]
    },
    {
      name: '💰 Business & Sales',
      items: [
        { name: 'Salesforce', actions: 'Crear leads, CRM' },
        { name: 'Stripe', actions: 'Procesar pagos' },
        { name: 'SAT México', actions: 'Descargar CFDI' },
        { name: 'Webhooks', actions: 'Triggers personalizados' }
      ]
    },
    {
      name: '📱 Messaging',
      items: [
        { name: 'Telegram', actions: 'Enviar mensajes' },
        { name: 'WhatsApp', actions: 'Templates de mensajes' }
      ]
    },
    {
      name: '🤖 IA & Automation',
      items: [
        { name: 'AI Agent Creator', actions: 'Crear agentes personalizados', locked: true },
        { name: 'RAG Handler', actions: 'Búsqueda semántica', locked: true },
        { name: 'Memory Systems', actions: 'Memoria episódica/semántica', locked: true },
        { name: 'LLM Integrations', actions: 'OpenAI, Claude, otros', locked: true }
      ]
    }
  ];

  const techCategories = [
    {
      name: '🎨 Frontend',
      items: ['Preact', 'Tailwind', 'TypeScript', 'Vite']
    },
    {
      name: '⚙️ Backend', 
      items: ['Python', 'FastAPI', 'PostgreSQL', 'Redis']
    },
    {
      name: '🧠 IA & NLP',
      items: ['OpenAI', 'Claude', 'Langchain', 'Vector DB']
    },
    {
      name: '☁️ Deploy',
      items: ['Docker', 'AWS', 'Railway', 'GitHub Actions']
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-main text-text-primary overflow-auto">
      <div className="max-w-7xl mx-auto px-6 py-10">
        {/* Header */}
        <header className="text-center mb-16">
          <div className="inline-flex items-center gap-4 mb-6 p-4 glass rounded-3xl">
            <div className="w-16 h-16 flex items-center justify-center">
              <img 
                src="/logo.svg" 
                alt="QYRAL Logo" 
                className="w-16 h-16"
                style={{ filter: 'none' }}
              />
            </div>
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold mb-4 gradient-text leading-tight">
            Plataforma de Automatización
          </h1>
          <p className="text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed">
            Conecta tus herramientas favoritas con inteligencia artificial y lenguaje natural para automatizar tu negocio
          </p>
          
          {/* Welcome message for authenticated users */}
          {isAuthenticated && (
            <div className="mt-8 max-w-lg mx-auto glass p-6 rounded-3xl border border-accent">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 surface-elevated rounded-full flex items-center justify-center text-2xl">
                  👋
                </div>
                <div className="text-left">
                  <h3 className="text-lg font-bold text-text-primary">¡Bienvenido de vuelta!</h3>
                  <p className="text-sm text-text-secondary">Listo para crear nuevas automatizaciones</p>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <Link href="/chat" className="btn-primary px-4 py-2 rounded-lg text-sm font-medium flex-1 text-center">
                  🚀 Crear Workflow
                </Link>
                <button className="btn-glass px-4 py-2 rounded-lg text-sm font-medium flex-1 text-center opacity-50 cursor-not-allowed">
                  🛒 Próximamente
                </button>
              </div>
            </div>
          )}
          
          {/* Call to Action para usuarios no autenticados */}
          {!isAuthenticated && (
            <div className="mt-8 max-w-md mx-auto">
              <button
                onClick={onLoginClick}
                className="btn-primary px-8 py-4 rounded-2xl font-bold text-lg shadow-elegant-lg hover:transform hover:scale-105 transition-all duration-300 flex items-center gap-3 mx-auto"
              >
                🚀 ¡Comenzar Gratis!
              </button>
              <p className="text-sm text-text-muted mt-3">
                Explora las funciones públicas o inicia sesión para acceso completo
              </p>
            </div>
          )}
        </header>

        {/* Navigation Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8 mb-20">
          {sections.map((section, index) => {
            const isLocked = (section.requiresAuth && !isAuthenticated) || section.locked;
            const CardContent = (
              <div 
                className={`relative block glass-card p-8 cursor-pointer overflow-hidden group animate-fadeInUp animate-delay-${(index + 1) * 100} ${
                  section.primary ? 'bg-gradient-card border-accent' : ''
                } ${isLocked ? 'opacity-75' : ''}`}
                onMouseEnter={() => !isLocked && setHoveredCard(section.id)}
                onMouseLeave={() => setHoveredCard(null)}
                onClick={isLocked ? (e) => { e.preventDefault(); onLoginClick(); } : undefined}
              >
                <div className="relative z-10">
                  <div className={`w-20 h-20 surface-elevated rounded-3xl flex items-center justify-center text-4xl mb-6 transition-all duration-300 ${
                    hoveredCard === section.id && !isLocked ? 'transform scale-110 rotate-3 shadow-elegant' : ''
                  }`}>
                    {section.icon}
                  </div>
                  <h3 className="text-2xl font-bold mb-3 text-text-primary">
                    {section.title}
                  </h3>
                  <p className="text-text-secondary mb-6 leading-relaxed">
                    {section.description}
                  </p>
                  <ul className="space-y-2">
                    {section.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-3 text-sm text-text-secondary">
                        <div className="w-1.5 h-1.5 bg-accent rounded-full flex-shrink-0"></div>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
                
                {/* Lock Overlay */}
                {isLocked && (
                  <div className="absolute inset-0 bg-gradient-main/80 backdrop-blur-sm flex flex-col items-center justify-center z-20 rounded-3xl">
                    <div className="w-16 h-16 surface-elevated rounded-2xl flex items-center justify-center text-3xl mb-4 shadow-elegant">
                      🔒
                    </div>
                    {section.locked ? (
                      <>
                        <h4 className="text-lg font-bold text-text-primary mb-2">Próximamente</h4>
                        <p className="text-sm text-text-secondary text-center max-w-[200px]">
                          Esta funcionalidad estará disponible pronto
                        </p>
                      </>
                    ) : (
                      <>
                        <h4 className="text-lg font-bold text-text-primary mb-2">¡Inicia sesión!</h4>
                        <p className="text-sm text-text-secondary text-center max-w-[200px] mb-4">
                          Necesitas una cuenta para acceder a esta funcionalidad
                        </p>
                        <button 
                          onClick={(e) => { e.stopPropagation(); onLoginClick(); }}
                          className="btn-primary px-4 py-2 rounded-lg text-sm font-semibold"
                        >
                          🔑 Acceder
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            );

            return isLocked ? (
              <div key={section.id}>
                {CardContent}
              </div>
            ) : (
              <Link key={section.id} href={section.href}>
                {CardContent}
              </Link>
            );
          })}
        </div>

        {/* How It Works */}
        <section className="text-center mb-20">
          <h2 className="text-4xl font-bold mb-12 gradient-text">
            ¿Cómo Funciona?
          </h2>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-8 sm:gap-12 max-w-4xl mx-auto flex-wrap">
            {flowSteps.map((step, index) => (
              <div key={step.step} className="flex flex-col items-center text-center relative">
                <div className="w-20 h-20 surface-elevated rounded-full flex items-center justify-center text-3xl font-bold shadow-elegant mb-4">
                  {step.step}
                </div>
                <div className="text-lg font-medium max-w-[120px] leading-tight">
                  {step.text}
                </div>
                {index < flowSteps.length - 1 && (
                  <div className="hidden md:block absolute -right-10 top-10 text-3xl text-accent font-bold">
                    →
                  </div>
                )}
                {index < flowSteps.length - 1 && (
                  <div className="md:hidden mt-4 text-3xl text-accent font-bold transform rotate-90">
                    →
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Benefits Section for Non-Authenticated Users */}
        {!isAuthenticated && (
          <section className="mb-20">
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold mb-4 gradient-text">
                ¿Por qué crear una cuenta?
              </h2>
              <p className="text-text-secondary max-w-2xl mx-auto">
                Desbloquea todas las funcionalidades y lleva tu productividad al siguiente nivel
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
              <div className="glass-card p-6 text-center">
                <div className="w-16 h-16 surface-elevated rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-elegant">
                  💬
                </div>
                <h3 className="text-xl font-bold mb-3 text-text-primary">Workflows Ilimitados</h3>
                <p className="text-text-secondary">Crea tantas automatizaciones como necesites sin restricciones</p>
              </div>
              
              <div className="glass-card p-6 text-center">
                <div className="w-16 h-16 surface-elevated rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-elegant">
                  📊
                </div>
                <h3 className="text-xl font-bold mb-3 text-text-primary">Analytics Avanzados</h3>
                <p className="text-text-secondary">Monitorea el rendimiento y optimiza tus automatizaciones</p>
              </div>
              
              <div className="glass-card p-6 text-center">
                <div className="w-16 h-16 surface-elevated rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-elegant">
                  🔐
                </div>
                <h3 className="text-xl font-bold mb-3 text-text-primary">Credenciales Seguras</h3>
                <p className="text-text-secondary">Gestiona tus integraciones de manera segura y cifrada</p>
              </div>
            </div>

            <div className="text-center">
              <button
                onClick={onLoginClick}
                className="btn-primary px-8 py-4 rounded-2xl font-bold text-lg shadow-elegant-lg hover:transform hover:scale-105 transition-all duration-300 inline-flex items-center gap-3"
              >
                🔑 Crear Cuenta Gratis
              </button>
            </div>
          </section>
        )}

        {/* OAuth Test Button - Solo para desarrollo */}
        {isAuthenticated && (
          <section className="mb-12 text-center">
            <div className="glass-card p-6 max-w-md mx-auto">
              <h3 className="text-lg font-bold mb-4">🧪 Probar OAuth</h3>
              <input
                type="text"
                value={testUserIntent}
                onChange={(e) => setTestUserIntent(e.target.value)}
                className="w-full p-3 surface-input border border-accent rounded-lg mb-4 text-text-primary"
                placeholder="Describe qué quieres automatizar..."
              />
              <button
                onClick={() => setShowAutoDiscovery(true)}
                className="btn-primary px-4 py-2 rounded-lg w-full"
              >
                🔗 Probar AutoDiscovery
              </button>
            </div>
          </section>
        )}

        {/* Integrations Section */}
        <section id="integrations-section" className="glass rounded-4xl p-8 md:p-12 mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-4 gradient-text">
              🔌 Integraciones Disponibles
            </h2>
            <p className="text-text-secondary max-w-2xl mx-auto">
              Conecta tus herramientas favoritas y automatiza tus procesos de negocio
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
            {integrationCategories.map((category, index) => (
              <div key={index} className="text-left">
                <h4 className="text-lg font-semibold mb-4 text-accent flex items-center gap-2">
                  {category.name}
                </h4>
                <div className="space-y-3">
                  {category.items.map((item, i) => (
                    <div 
                      key={i}
                      className={`p-3 surface-elevated border rounded-lg transition-all duration-300 relative overflow-hidden ${
                        item.locked 
                          ? 'border-gray-600 opacity-75' 
                          : 'border-accent/30 hover:surface-card hover:border-accent hover:transform hover:-translate-y-0.5'
                      }`}
                    >
                      <div className={`font-medium mb-1 ${item.locked ? 'text-gray-400' : 'text-text-primary'}`}>
                        {item.name}
                        {item.locked && (
                          <span className="ml-2 text-xs">🔒</span>
                        )}
                      </div>
                      <div className={`text-sm ${item.locked ? 'text-gray-500' : 'text-text-secondary'}`}>
                        {item.locked ? 'Próximamente...' : item.actions}
                      </div>
                      
                      {/* Lock overlay for locked items */}
                      {item.locked && (
                        <div className="absolute inset-0 bg-gradient-main/60 backdrop-blur-[1px] flex items-center justify-center rounded-lg">
                          <div className="text-center">
                            <div className="text-2xl mb-1">🔒</div>
                            <div className="text-xs font-medium text-gray-300">Próximamente</div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Tech Stack */}
        <section className="glass rounded-4xl p-8 md:p-12 text-center">
          <h2 className="text-3xl font-bold mb-8 gradient-text">
            Stack Tecnológico
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8">
            {techCategories.map((category, index) => (
              <div key={index} className="text-left">
                <h4 className="text-lg font-semibold mb-4 text-accent">
                  {category.name}
                </h4>
                <div className="flex flex-wrap gap-2">
                  {category.items.map((item, i) => (
                    <span 
                      key={i}
                      className="px-3 py-1.5 surface-elevated border border-accent text-text-primary rounded-full text-sm font-medium transition-all duration-300 hover:surface-card hover:transform hover:-translate-y-0.5"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* File Discovery Modal */}
      <FileDiscoveryModal
        isOpen={showAutoDiscovery}
        onClose={() => setShowAutoDiscovery(false)}
        userIntent={testUserIntent}
        onFileSelected={(file) => {
          console.log('Archivo seleccionado:', file);
          setShowAutoDiscovery(false);
        }}
      />
    </div>
  );
};

// Nombrar el componente explícitamente para Prefresh
Dashboard.displayName = 'Dashboard';

export default Dashboard;