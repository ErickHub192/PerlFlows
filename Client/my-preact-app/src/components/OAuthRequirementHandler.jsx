import { useState, useEffect } from 'preact/hooks';
import AuthFlow from './AuthFlow';

const OAuthRequirementHandler = ({ oauthRequirements, chatId, onAllCompleted, onError }) => {
  const [currentRequirement, setCurrentRequirement] = useState(null);
  const [completedProviders, setCompletedProviders] = useState([]);
  const [pendingRequirements, setPendingRequirements] = useState([]);

  useEffect(() => {
    if (oauthRequirements && Array.isArray(oauthRequirements)) {
      setPendingRequirements(oauthRequirements);
      setCurrentRequirement(oauthRequirements[0]);
    }
  }, [oauthRequirements]);

  const handleAuthSuccess = (authData) => {
    console.log('🔥 OAuthRequirementHandler - handleAuthSuccess called with:', authData);
    const currentServiceId = currentRequirement?.service_id;
    console.log('🔥 OAuthRequirementHandler - currentServiceId:', currentServiceId);
    console.log('🔥 OAuthRequirementHandler - completedProviders before:', completedProviders);
    console.log('🔥 OAuthRequirementHandler - pendingRequirements before:', pendingRequirements);
    
    if (currentServiceId) {
      const newCompleted = [...completedProviders, currentServiceId];
      setCompletedProviders(newCompleted);
      console.log('🔥 OAuthRequirementHandler - newCompleted:', newCompleted);
      
      // Remove current requirement from pending
      const remaining = pendingRequirements.filter(req => req.service_id !== currentServiceId);
      setPendingRequirements(remaining);
      console.log('🔥 OAuthRequirementHandler - remaining after filter:', remaining);
      
      if (remaining.length > 0) {
        // Move to next requirement
        console.log('🔥 OAuthRequirementHandler - Moving to next requirement:', remaining[0]);
        setCurrentRequirement(remaining[0]);
      } else {
        // ✅ FIX: ALL OAuth requirements completed - only now trigger callback
        console.log('🎉 OAuthRequirementHandler - ALL OAUTH REQUIREMENTS COMPLETED!');
        console.log('🎉 Total services authenticated:', newCompleted.length);
        console.log('🎉 Services:', newCompleted);
        setCurrentRequirement(null);
        
        if (onAllCompleted) {
          console.log('🎉 OAuthRequirementHandler - Executing onAllCompleted callback for ALL services');
          onAllCompleted(newCompleted, authData);
        } else {
          console.error('❌ OAuthRequirementHandler - onAllCompleted callback is missing!');
        }
      }
    } else {
      console.error('❌ OAuthRequirementHandler - No currentServiceId found');
    }
  };

  const handleAuthError = (error) => {
    console.error('OAuth requirement auth error:', error);
    onError && onError(error, currentRequirement);
  };

  const handleClose = () => {
    setCurrentRequirement(null);
    // Optionally notify parent that user cancelled
    onError && onError('User cancelled authentication', currentRequirement);
  };

  if (!currentRequirement) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Autenticación Requerida
          </h3>
          <p className="text-sm text-gray-600 mt-2">
            Para continuar con el workflow, necesitas autenticarte con{' '}
            <span className="font-medium">{currentRequirement.service_name || currentRequirement.service_id}</span>
          </p>
          
          {pendingRequirements.length > 1 && (
            <p className="text-xs text-gray-500 mt-1">
              {completedProviders.length + 1} de {pendingRequirements.length + completedProviders.length} servicios
            </p>
          )}
        </div>

        <AuthFlow
          isOpen={true}
          onClose={handleClose}
          serviceId={currentRequirement.service_id}
          chatId={chatId}
          onSuccess={handleAuthSuccess}
          onError={handleAuthError}
        />
      </div>
    </div>
  );
};

export default OAuthRequirementHandler;