import { useState } from 'preact/hooks';
import useOAuthApps from '../hooks/useOAuthApps';

const OAuthAppManager = () => {
    const {
        oauthApps,
        loading,
        error,
        createOAuthApp,
        updateOAuthApp,
        deleteOAuthApp,
        hasOAuthApp
    } = useOAuthApps();

    const [showForm, setShowForm] = useState(false);
    const [editingProvider, setEditingProvider] = useState(null);
    const [formData, setFormData] = useState({
        provider: '',
        client_id: '',
        client_secret: '',
        app_name: ''
    });

    // Providers soportados
    const supportedProviders = [
        { id: 'google', name: 'Google', icon: '🔍', description: 'Gmail, Drive, Calendar, Sheets' },
        { id: 'github', name: 'GitHub', icon: '🐙', description: 'Repositorios, Issues, Pull Requests' },
        { id: 'microsoft', name: 'Microsoft', icon: '🔷', description: 'Outlook, Office 365, OneDrive' },
        { id: 'slack', name: 'Slack', icon: '💬', description: 'Mensajería de equipo' },
        { id: 'salesforce', name: 'Salesforce', icon: '☁️', description: 'CRM y automatización' }
    ];

    const handleOpenForm = (provider = null) => {
        if (provider) {
            // Editando OAuth app existente
            const existingApp = oauthApps.find(app => app.provider === provider);
            setFormData({
                provider,
                client_id: existingApp?.client_id || '',
                client_secret: '', // No mostramos el secret por seguridad
                app_name: existingApp?.app_name || ''
            });
            setEditingProvider(provider);
        } else {
            // Nueva OAuth app
            setFormData({
                provider: '',
                client_id: '',
                client_secret: '',
                app_name: ''
            });
            setEditingProvider(null);
        }
        setShowForm(true);
    };

    const handleCloseForm = () => {
        setShowForm(false);
        setEditingProvider(null);
        setFormData({ provider: '', client_id: '', client_secret: '', app_name: '' });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        try {
            if (editingProvider) {
                // Actualizar OAuth app existente
                const updateData = {};
                if (formData.client_id) updateData.client_id = formData.client_id;
                if (formData.client_secret) updateData.client_secret = formData.client_secret;
                if (formData.app_name) updateData.app_name = formData.app_name;
                
                await updateOAuthApp(editingProvider, updateData);
                alert('✅ OAuth App actualizada exitosamente');
            } else {
                // Crear nueva OAuth app
                await createOAuthApp(formData.provider, {
                    client_id: formData.client_id,
                    client_secret: formData.client_secret,
                    app_name: formData.app_name
                });
                alert('✅ OAuth App creada exitosamente');
            }
            
            handleCloseForm();
        } catch (error) {
            alert(`❌ Error: ${error.message}`);
        }
    };

    const handleDelete = async (provider) => {
        if (confirm(`¿Estás seguro de que quieres eliminar la OAuth App de ${provider}? Las futuras autenticaciones usarán las credenciales por defecto del sistema.`)) {
            try {
                await deleteOAuthApp(provider);
                alert('✅ OAuth App eliminada exitosamente');
            } catch (error) {
                alert(`❌ Error eliminando OAuth App: ${error.message}`);
            }
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900">🔧 Mis OAuth Applications</h3>
                    <p className="text-sm text-gray-600 mt-1">
                        Configura tus propias aplicaciones OAuth o usa las credenciales por defecto
                    </p>
                </div>
                <button
                    onClick={() => handleOpenForm()}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                >
                    ➕ Agregar OAuth App
                </button>
            </div>

            {/* Loading/Error */}
            {loading && (
                <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                </div>
            )}

            {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-red-600 text-sm">{error}</p>
                </div>
            )}

            {/* Providers Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {supportedProviders.map(provider => {
                    const userApp = oauthApps.find(app => app.provider === provider.id);
                    const hasApp = !!userApp;

                    return (
                        <div key={provider.id} className="border rounded-lg p-4">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center">
                                    <span className="text-2xl mr-3">{provider.icon}</span>
                                    <div>
                                        <h4 className="font-medium text-gray-900">{provider.name}</h4>
                                        <p className="text-xs text-gray-500">{provider.description}</p>
                                    </div>
                                </div>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                    hasApp 
                                        ? 'bg-green-100 text-green-800' 
                                        : 'bg-gray-100 text-gray-600'
                                }`}>
                                    {hasApp ? '✅ Configurado' : '⚙️ Por defecto'}
                                </span>
                            </div>

                            {hasApp && (
                                <div className="mb-3 p-2 bg-blue-50 rounded text-sm">
                                    <p className="text-blue-700">
                                        <strong>App:</strong> {userApp.app_name}
                                    </p>
                                    <p className="text-blue-600 text-xs mt-1">
                                        Client ID: {userApp.client_id.substring(0, 20)}...
                                    </p>
                                </div>
                            )}

                            <div className="flex space-x-2">
                                {hasApp ? (
                                    <>
                                        <button
                                            onClick={() => handleOpenForm(provider.id)}
                                            className="flex-1 text-blue-600 hover:text-blue-800 text-sm"
                                        >
                                            ✏️ Editar
                                        </button>
                                        <button
                                            onClick={() => handleDelete(provider.id)}
                                            className="flex-1 text-red-600 hover:text-red-800 text-sm"
                                        >
                                            🗑️ Eliminar
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        onClick={() => handleOpenForm(provider.id)}
                                        className="w-full text-blue-600 hover:text-blue-800 text-sm"
                                    >
                                        ⚙️ Configurar
                                    </button>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Form Modal */}
            {showForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                        <div className="px-6 py-4 border-b">
                            <h3 className="text-lg font-semibold">
                                {editingProvider ? '✏️ Editar OAuth App' : '➕ Nueva OAuth App'}
                            </h3>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            {!editingProvider && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Provider
                                    </label>
                                    <select
                                        value={formData.provider}
                                        onChange={(e) => setFormData({...formData, provider: e.target.value})}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        required
                                    >
                                        <option value="">Seleccionar provider...</option>
                                        {supportedProviders.map(p => (
                                            <option key={p.id} value={p.id} disabled={hasOAuthApp(p.id)}>
                                                {p.name} {hasOAuthApp(p.id) ? '(Ya configurado)' : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Nombre de la App
                                </label>
                                <input
                                    type="text"
                                    value={formData.app_name}
                                    onChange={(e) => setFormData({...formData, app_name: e.target.value})}
                                    placeholder="Ej: Mi App de Gmail Personal"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Client ID
                                </label>
                                <input
                                    type="text"
                                    value={formData.client_id}
                                    onChange={(e) => setFormData({...formData, client_id: e.target.value})}
                                    placeholder="123456789-abcdef.apps.googleusercontent.com"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Client Secret
                                </label>
                                <input
                                    type="password"
                                    value={formData.client_secret}
                                    onChange={(e) => setFormData({...formData, client_secret: e.target.value})}
                                    placeholder={editingProvider ? "Dejar vacío para mantener el actual" : "GOCSPX-1234567890abcdef"}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    required={!editingProvider}
                                />
                            </div>

                            <div className="flex space-x-3 pt-4">
                                <button
                                    type="button"
                                    onClick={handleCloseForm}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                                >
                                    {editingProvider ? 'Actualizar' : 'Crear'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default OAuthAppManager;