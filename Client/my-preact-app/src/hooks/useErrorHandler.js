// src/hooks/useErrorHandler.js

import { useState, useCallback, useRef } from 'preact/hooks';
import useNotificationStore from '../stores/notificationStore';
import { logoutLocal } from './useAuth';

// ============================================
// ESTRATEGIAS DE MANEJO DE ERRORES
// ============================================

class ValidationErrorStrategy {
  constructor(notifier) {
    this.notifier = notifier;
  }

  handle(error) {
    const errors = error.response?.data?.errors || error.data?.errors || {};
    
    // Si hay errores específicos de campos, los devolvemos para el formulario
    if (Object.keys(errors).length > 0) {
      return { fieldErrors: errors };
    }
    
    // Error de validación genérico
    this.notifier.notify('Por favor verifica los datos ingresados', 'warning');
    return { fieldErrors: {} };
  }
}

class AuthErrorStrategy {
  constructor(notifier) {
    this.notifier = notifier;
  }

  handle(error) {
    // Limpiar autenticación
    logoutLocal();
    
    // Notificar y redirigir
    this.notifier.notify('Tu sesión ha expirado', 'warning');
    
    // Redirigir después de un momento
    setTimeout(() => {
      window.location.href = '/';
    }, 2000);
    
    return { shouldRedirect: true };
  }
}

class NetworkErrorStrategy {
  constructor(notifier) {
    this.notifier = notifier;
  }

  handle(error) {
    this.notifier.notify('Error de conexión. Verifica tu internet', 'error');
    return { isNetworkError: true };
  }
}

class ServerErrorStrategy {
  constructor(notifier) {
    this.notifier = notifier;
  }

  handle(error) {
    this.notifier.notify('Error del servidor. Intenta más tarde', 'error');
    this.logError(error);
    return { isServerError: true };
  }

  logError(error) {
    console.error('Server Error:', {
      status: error.status,
      message: error.message,
      url: error.config?.url,
      timestamp: new Date().toISOString()
    });
  }
}

class DefaultErrorStrategy {
  constructor(notifier) {
    this.notifier = notifier;
  }

  handle(error) {
    const message = error.message || 'Ha ocurrido un error inesperado';
    this.notifier.notify(message, 'error');
    console.error('Unhandled error:', error);
    return { isUnknownError: true };
  }
}

// ============================================
// FACTORY PARA ESTRATEGIAS
// ============================================

class ErrorStrategyFactory {
  constructor(notifier) {
    this.notifier = notifier;
    this.strategies = new Map([
      ['validation', () => new ValidationErrorStrategy(this.notifier)],
      ['auth', () => new AuthErrorStrategy(this.notifier)],
      ['network', () => new NetworkErrorStrategy(this.notifier)],
      ['server', () => new ServerErrorStrategy(this.notifier)],
      ['default', () => new DefaultErrorStrategy(this.notifier)]
    ]);
  }

  create(errorType) {
    const createStrategy = this.strategies.get(errorType) || this.strategies.get('default');
    return createStrategy();
  }

  getErrorType(error) {
    // Error de validación
    if (error.status === 422 || error.status === 400) {
      return 'validation';
    }
    
    // Error de autenticación/autorización
    if (error.status === 401 || error.status === 403) {
      return 'auth';
    }
    
    // Error de servidor
    if (error.status >= 500) {
      return 'server';
    }
    
    // Error de red (sin status o falla de conexión)
    if (!error.status || error.name === 'NetworkError' || error.code === 'NETWORK_ERROR') {
      return 'network';
    }
    
    return 'default';
  }
}

// ============================================
// HOOK PRINCIPAL
// ============================================

export function useErrorHandler() {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { addNotification } = useNotificationStore();

  // Creamos el factory una sola vez
  const factoryRef = useRef(new ErrorStrategyFactory({
    notify: (message, type = 'error') => addNotification({
      type,
      message,
      duration: 5000
    })
  }));

  const handleError = useCallback((error, context = {}) => {
    console.error('Error handled:', error, context);
    
    // Determinar tipo de error y aplicar estrategia
    const errorType = factoryRef.current.getErrorType(error);
    const strategy = factoryRef.current.create(errorType);
    const result = strategy.handle(error);
    
    // Establecer error en estado local
    setError({
      original: error,
      type: errorType,
      context,
      result,
      timestamp: Date.now()
    });

    return result;
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Wrapper para funciones async que maneja errores automáticamente
  const withErrorHandler = useCallback((asyncFn, context = {}) => {
    return async (...args) => {
      try {
        setLoading(true);
        clearError();
        const result = await asyncFn(...args);
        return result;
      } catch (err) {
        const errorResult = handleError(err, { ...context, args });
        throw { ...err, errorResult }; // Re-throw con info adicional
      } finally {
        setLoading(false);
      }
    };
  }, [handleError, clearError]);

  // Versión "safe" que no re-lanza el error
  const safeAsync = useCallback((asyncFn, context = {}) => {
    return async (...args) => {
      try {
        setLoading(true);
        clearError();
        const result = await asyncFn(...args);
        return { data: result, error: null };
      } catch (err) {
        const errorResult = handleError(err, { ...context, args });
        return { data: null, error: err, errorResult };
      } finally {
        setLoading(false);
      }
    };
  }, [handleError, clearError]);

  return {
    error,
    loading,
    handleError,
    clearError,
    withErrorHandler,
    safeAsync
  };
}