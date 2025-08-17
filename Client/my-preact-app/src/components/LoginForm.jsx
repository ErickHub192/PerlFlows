// src/components/LoginForm.jsx

import { useState, useEffect, useRef } from 'preact/hooks';
import { fetcher } from '../api/fetcher';
import { useAuth } from '../hooks/useAuth';

export default function LoginForm({ onClose }) {
  const { login: authLogin } = useAuth();

  const [isRegistering, setIsRegistering] = useState(false);
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [registerData, setRegisterData] = useState({ email: '', username: '', password: '' });
  const [loginError, setLoginError] = useState('');
  const [registerError, setRegisterError] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const userInputRef = useRef(null);
  const modalRef = useRef(null);

  useEffect(() => {
    // Al montar, limpiar campos/errores y enfocar
    setLoginData({ username: '', password: '' });
    setRegisterData({ email: '', username: '', password: '' });
    setLoginError('');
    setRegisterError('');

    // Mostrar aviso de sesión expirada si viene de interceptor 401
    if (sessionStorage.getItem('sessionExpired')) {
      setInfoMessage('Tu sesión expiró. Por favor, inicia sesión de nuevo.');
      sessionStorage.removeItem('sessionExpired');
    }

    // Focus después de un pequeño delay para asegurar que el modal esté montado
    setTimeout(() => {
      userInputRef.current?.focus();
    }, 100);

    // Cerrar modal con ESC
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleLogin = async () => {
    setLoginError('');
    setIsLoading(true);
    try {
      const data = await fetcher('/api/auth/login', {
        method: 'POST',
        body: loginData,
      });

      authLogin(data.access_token, data.refresh_token);
      onClose();
      // Small delay to allow modal to close before refresh
      setTimeout(() => {
        window.location.href = '/';
      }, 300);
    } catch (err) {
      setLoginError(err.message || 'Error al iniciar sesión');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async () => {
    setRegisterError('');
    setIsLoading(true);
    try {
      const data = await fetcher('/api/auth/register', {
        method: 'POST',
        body: registerData,
      });

      authLogin(data.access_token);
      onClose();
      setTimeout(() => {
        window.location.href = '/';
      }, 300);
    } catch (err) {
      setRegisterError(err.message || 'Error en el registro');
    } finally {
      setIsLoading(false);
    }
  };

  // Click outside to close
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-gradient-main/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div 
        ref={modalRef}
        className="relative glass-card p-8 w-full max-w-md animate-fadeInUp shadow-elegant-lg border border-accent"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 surface-elevated rounded-xl flex items-center justify-center text-text-secondary hover:text-text-primary transition-colors focus-elegant"
        >
          ✕
        </button>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 surface-elevated rounded-3xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-elegant">
            🔑
          </div>
          <h2 className="text-2xl font-bold gradient-text-elegant mb-2">
            {isRegistering ? 'Crear Cuenta' : 'Iniciar Sesión'}
          </h2>
          <p className="text-subtle text-sm">
            {isRegistering 
              ? 'Crea tu cuenta para acceder a todas las funciones' 
              : 'Accede a tu cuenta para gestionar tus automatizaciones'
            }
          </p>
        </div>

        {/* Info Message */}
        {infoMessage && (
          <div className="mb-6 p-3 surface-elevated rounded-xl border-l-4 border-yellow-400">
            <p className="text-yellow-300 text-sm">{infoMessage}</p>
          </div>
        )}

        {/* Form */}
        {isRegistering ? (
          <RegisterForm
            data={registerData}
            setData={setRegisterData}
            error={registerError}
            onSubmit={handleRegister}
            isLoading={isLoading}
            onToggle={() => {
              setRegisterError('');
              setLoginError('');
              setIsRegistering(false);
              setTimeout(() => userInputRef.current?.focus(), 100);
            }}
          />
        ) : (
          <LoginFormContent
            data={loginData}
            setData={setLoginData}
            error={loginError}
            onSubmit={handleLogin}
            isLoading={isLoading}
            onToggle={() => {
              setRegisterError('');
              setLoginError('');
              setIsRegistering(true);
            }}
            inputRef={userInputRef}
          />
        )}
      </div>
    </div>
  );
}

function LoginFormContent({ data, setData, error, onSubmit, onToggle, inputRef, isLoading }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      onSubmit();
    }
  };

  return (
    <>
      {error && (
        <div className="mb-4 p-3 surface-elevated rounded-xl border-l-4 border-red-400">
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-subtle mb-2">
            Usuario
          </label>
          <input
            ref={inputRef}
            type="text"
            placeholder="Ingresa tu usuario"
            value={data.username}
            onInput={(e) => setData({ ...data, username: e.currentTarget.value })}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all disabled:opacity-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-subtle mb-2">
            Contraseña
          </label>
          <input
            type="password"
            placeholder="Ingresa tu contraseña"
            value={data.password}
            onInput={(e) => setData({ ...data, password: e.currentTarget.value })}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all disabled:opacity-50"
          />
        </div>
      </div>

      <button 
        onClick={onSubmit} 
        disabled={isLoading || !data.username.trim() || !data.password.trim()}
        className="w-full btn-primary py-3 rounded-xl font-semibold text-white mb-4 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            Iniciando sesión...
          </>
        ) : (
          'Iniciar Sesión'
        )}
      </button>

      <p className="text-center text-sm text-subtle">
        ¿No tienes cuenta?{' '}
        <button 
          onClick={onToggle} 
          disabled={isLoading}
          className="text-accent hover:text-accent-hover underline font-medium transition-colors disabled:opacity-50"
        >
          Crear cuenta
        </button>
      </p>
    </>
  );
}

function RegisterForm({ data, setData, error, onSubmit, onToggle, isLoading }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      onSubmit();
    }
  };

  const isFormValid = data.email.trim() && data.username.trim() && data.password.trim();

  return (
    <>
      {error && (
        <div className="mb-4 p-3 surface-elevated rounded-xl border-l-4 border-red-400">
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-subtle mb-2">
            Email
          </label>
          <input
            type="email"
            placeholder="tu@email.com"
            value={data.email}
            onInput={(e) => setData({ ...data, email: e.currentTarget.value })}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all disabled:opacity-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-subtle mb-2">
            Usuario
          </label>
          <input
            type="text"
            placeholder="Elige un nombre de usuario"
            value={data.username}
            onInput={(e) => setData({ ...data, username: e.currentTarget.value })}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all disabled:opacity-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-subtle mb-2">
            Contraseña
          </label>
          <input
            type="password"
            placeholder="Crea una contraseña segura"
            value={data.password}
            onInput={(e) => setData({ ...data, password: e.currentTarget.value })}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all disabled:opacity-50"
          />
        </div>
      </div>

      <button 
        onClick={onSubmit} 
        disabled={isLoading || !isFormValid}
        className="w-full btn-primary py-3 rounded-xl font-semibold text-white mb-4 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            Creando cuenta...
          </>
        ) : (
          'Crear Cuenta'
        )}
      </button>

      <p className="text-center text-sm text-text-secondary">
        ¿Ya tienes cuenta?{' '}
        <button 
          onClick={onToggle} 
          disabled={isLoading}
          className="text-accent hover:text-accent-hover underline font-medium transition-colors disabled:opacity-50"
        >
          Iniciar sesión
        </button>
      </p>
    </>
  );
}

