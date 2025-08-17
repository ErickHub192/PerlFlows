import { useState, useEffect } from 'preact/hooks';
import AuthFlow from './AuthFlow';
import OAuthAppManager from './OAuthAppManager';
import useCredentials from '../hooks/useCredentials';
import { fetcher } from '../api/fetcher';

const CredentialsManager = ({ isOpen, onClose }) => {
    const [authFlowOpen, setAuthFlowOpen] = useState(false);
    const [currentAuthProvider, setCurrentAuthProvider] = useState(null);
    const [selectedProvider, setSelectedProvider] = useState('');
    const [selectedFlavor, setSelectedFlavor] = useState('');
    const [activeTab, setActiveTab] = useState('credentials');
    
    const { 
        credentials, 
        loading, 
        error, 
        refreshCredentials, 
        deleteCredential,
        getConnectionStatus 
    } = useCredentials();

    // ✅ Servicios obtenidos dinámicamente desde la API (elimina hardcodeo)
    const [availableServices, setAvailableServices] = useState({});
    const [servicesLoading, setServicesLoading] = useState(true);

    // ✅ NUEVO: Cargar servicios desde API agnóstica
    useEffect(() => {
        const loadAvailableServices = async () => {
            try {
                const data = await fetcher('/api/v1/auth-service-discovery/services/available');
                
                // Organizar servicios por categoría según mechanism
                const servicesByCategory = data.reduce((acc, service) => {
                    const category = service.mechanism === 'oauth2' ? 'OAuth Services' : 
                                   service.mechanism === 'api_key' ? 'API Key Services' :
                                   service.mechanism === 'bot_token' ? 'Bot Token Services' :
                                   service.mechanism === 'db_credentials' ? 'Database Services' : 'Otros';
                    if (!acc[category]) acc[category] = [];
                    acc[category].push({
                        service_id: service.service_id,
                        name: service.display_name || service.service_id,
                        icon: getServiceIcon(service.service_id, service.mechanism),
                        mechanism: service.mechanism,
                        provider: service.provider
                    });
                    return acc;
                }, {});
                
                setAvailableServices(servicesByCategory);
            } catch (error) {
                console.error('Error loading services:', error);
                setAvailableServices({});
            } finally {
                setServicesLoading(false);
            }
        };

        loadAvailableServices();
    }, []);

    // Helper para obtener iconos por servicio
    const getServiceIcon = (serviceId, mechanism) => {
        const icons = {
            gmail: '📧', google_calendar: '📅', google_drive: '💾', google_sheets: '📊',
            slack: '💬', telegram: '✈️', stripe: '💳', github: '🐙',
            dropbox: '📦', salesforce: '☁️', hubspot: '🎯', airtable: '📋',
            postgres: '🐘', sat: '🏛️', whatsapp: '📱', outlook: '📮'
        };
        return icons[serviceId] || (mechanism === 'oauth2' ? '🔐' : 
                                   mechanism === 'api_key' ? '🔑' :
                                   mechanism === 'bot_token' ? '🤖' : '🔗');
    };

    // Helper para obtener info de un servicio por service_id
    const getServiceInfo = (serviceId) => {
        for (const services of Object.values(availableServices)) {
            const service = services.find(s => s.service_id === serviceId);
            if (service) return service;
        }
        return { icon: '🔐', name: serviceId };
    };

    const handleAddCredential = (serviceId) => {
        setCurrentAuthProvider({ service_id: serviceId });
        setAuthFlowOpen(true);
    };

    const handleAuthSuccess = async (credential) => {
        await refreshCredentials();
        setAuthFlowOpen(false);
        setCurrentAuthProvider(null);
    };

    const handleAuthError = (error) => {
        console.error('Auth failed:', error);
        setAuthFlowOpen(false);
        setCurrentAuthProvider(null);
    };

    const handleDeleteCredential = async (serviceId) => {
        // ✅ FIX: Buscar info del servicio para mostrar nombre amigable
        const serviceInfo = getServiceInfo(serviceId);
        const displayName = serviceInfo.name || serviceId;
        
        if (confirm(`¿Estás seguro de que quieres eliminar la credencial de ${displayName}?`)) {
            try {
                // ✅ FIX: Usar service_id directamente (sin flavor)
                await deleteCredential(serviceId);  
                console.log('✅ Credencial eliminada exitosamente:', serviceId);
            } catch (error) {
                console.error('❌ Error eliminando credencial:', error);
                alert(`Error eliminando credencial de ${displayName}: ${error.message}`);
            }
        }
    };

    const getCredentialAge = (createdAt) => {
        const now = new Date();
        const created = new Date(createdAt);
        const diffHours = Math.floor((now - created) / (1000 * 60 * 60));
        
        if (diffHours < 1) return 'Hace menos de 1 hora';
        if (diffHours < 24) return `Hace ${diffHours} hora${diffHours > 1 ? 's' : ''}`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `Hace ${diffDays} día${diffDays > 1 ? 's' : ''}`;
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'connected': return 'text-green-600 bg-green-100';
            case 'expired': return 'text-orange-600 bg-orange-100';
            case 'disconnected': return 'text-gray-600 bg-gray-100';
            default: return 'text-gray-600 bg-gray-100';
        }
    };

    const getStatusText = (status) => {
        switch (status) {
            case 'connected': return 'Conectado';
            case 'expired': return 'Expirado';
            case 'disconnected': return 'Desconectado';
            default: return 'Desconocido';
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-70 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="glass-card rounded-xl shadow-elegant-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
                <div className="px-6 py-4 border-b border-primary">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-semibold text-elegant gradient-text">🔐 Gestión de Credenciales</h2>
                        <button
                            onClick={onClose}
                            className="text-subtle hover:text-white transition-colors p-2 hover:bg-white hover:bg-opacity-10 rounded-lg"
                        >
                            ✕
                        </button>
                    </div>
                    <p className="text-subtle text-sm mt-1">
                        Gestiona las conexiones con tus servicios y aplicaciones
                    </p>
                </div>
                
                {/* Tabs Navigation */}
                <div className="border-b border-primary px-6">
                    <nav className="flex space-x-8">
                        <button
                            onClick={() => setActiveTab('credentials')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                                activeTab === 'credentials'
                                    ? 'border-accent text-accent'
                                    : 'border-transparent text-subtle hover:text-elegant hover:border-primary'
                            }`}
                        >
                            🔐 Credenciales Activas
                        </button>
                        <button
                            onClick={() => setActiveTab('oauth-apps')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                                activeTab === 'oauth-apps'
                                    ? 'border-accent text-accent'
                                    : 'border-transparent text-subtle hover:text-elegant hover:border-primary'
                            }`}
                        >
                            🔧 OAuth Applications
                        </button>
                    </nav>
                </div>
                
                <div className="flex h-full" style={{ maxHeight: 'calc(90vh - 160px)' }}>
                    {activeTab === 'credentials' ? (
                        <>
                            {/* Panel izquierdo - Credenciales existentes */}
                            <div className="w-1/2 border-r border-primary overflow-y-auto p-6">
                        <h3 className="text-lg font-medium text-elegant mb-4">Credenciales Activas</h3>
                        
                        {loading && (
                            <div className="text-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto mb-2"></div>
                                <p className="text-subtle">Cargando credenciales...</p>
                            </div>
                        )}
                        
                        {error && (
                            <div className="surface-elevated border border-red-400 border-opacity-30 rounded-lg p-4 mb-4">
                                <p className="text-red-300 text-sm">{error}</p>
                            </div>
                        )}
                        
                        {!loading && credentials.length === 0 && (
                            <div className="text-center py-8">
                                <div className="text-subtle text-6xl mb-4">🔒</div>
                                <h4 className="text-elegant font-medium mb-2">No hay credenciales</h4>
                                <p className="text-muted text-sm">
                                    Añade tu primera conexión desde el panel derecho
                                </p>
                            </div>
                        )}
                        
                        <div className="space-y-3">
                            {credentials.map((cred, index) => {
                                const serviceInfo = getServiceInfo(cred.service_id);
                                const status = getConnectionStatus(cred.service_id);
                                return (
                                    <div key={index} className="border rounded-lg p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center">
                                                <span className="text-2xl mr-3">
                                                    {serviceInfo.icon}
                                                </span>
                                                <div>
                                                    <h4 className="font-medium">
                                                        {serviceInfo.name}
                                                    </h4>
                                                    <p className="text-xs text-gray-500">
                                                        {getCredentialAge(cred.created_at)} • {cred.service_id}
                                                    </p>
                                                </div>
                                            </div>
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
                                                {getStatusText(status)}
                                            </span>
                                        </div>
                                        
                                        <div className="flex justify-end space-x-2">
                                            {status === 'expired' && (
                                                <button
                                                    onClick={() => handleAddCredential(cred.service_id)}
                                                    className="text-orange-600 hover:text-orange-800 text-sm"
                                                >
                                                    🔄 Renovar
                                                </button>
                                            )}
                                            <button
                                                onClick={() => handleDeleteCredential(cred.service_id)}
                                                className="text-red-600 hover:text-red-800 text-sm"
                                            >
                                                🗑️ Eliminar
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                    
                            {/* Panel derecho - Añadir nuevas credenciales */}
                            <div className="w-1/2 overflow-y-auto p-6">
                        <h3 className="text-lg font-medium mb-4">Añadir Nueva Conexión</h3>
                        
                        {servicesLoading ? (
                            <div className="text-center py-8">
                                <div className="text-gray-500">Cargando servicios disponibles...</div>
                            </div>
                        ) : (
                            Object.entries(availableServices).map(([category, services]) => (
                                <div key={category} className="mb-6">
                                    <h4 className="text-sm font-medium text-gray-700 mb-3">{category}</h4>
                                    <div className="grid grid-cols-1 gap-2">
                                        {services.map((service, index) => (
                                            <button
                                                key={index}
                                                onClick={() => handleAddCredential(service.service_id)}
                                                className="flex items-center p-3 border rounded-lg hover:bg-gray-50 text-left"
                                            >
                                                <span className="text-2xl mr-3">{service.icon}</span>
                                                <div>
                                                    <div className="font-medium">{service.name}</div>
                                                    <div className="text-xs text-gray-500">
                                                        {service.mechanism} • {service.service_id}
                                                    </div>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ))
                        )}
                            </div>
                        </>
                    ) : (
                        /* OAuth Apps Manager */
                        <div className="w-full overflow-y-auto p-6">
                            <OAuthAppManager />
                        </div>
                    )}
                </div>
                
                {/* AuthFlow Modal */}
                <AuthFlow
                    isOpen={authFlowOpen}
                    onClose={() => setAuthFlowOpen(false)}
                    serviceId={currentAuthProvider?.service_id}
                    onSuccess={handleAuthSuccess}
                />
            </div>
        </div>
    );
};

export default CredentialsManager;