// Frontend Logger - Automatic file logging like backend
class FrontendLogger {
  constructor() {
    this.logEndpoint = '/api/frontend-logs';
    this.logBuffer = [];
    this.maxBufferSize = 50;
    this.flushInterval = 5000; // 5 seconds
    this.setupAutoFlush();
    this.interceptConsole();
  }

  interceptConsole() {
    // Store original console methods
    this.originalConsole = {
      log: console.log,
      info: console.info,
      warn: console.warn,
      error: console.error,
      debug: console.debug
    };

    // Override console methods to also send to backend
    console.log = (...args) => {
      this.originalConsole.log(...args);
      this.addLog('INFO', args);
    };

    console.info = (...args) => {
      this.originalConsole.info(...args);
      this.addLog('INFO', args);
    };

    console.warn = (...args) => {
      this.originalConsole.warn(...args);
      this.addLog('WARN', args);
    };

    console.error = (...args) => {
      this.originalConsole.error(...args);
      this.addLog('ERROR', args);
    };

    console.debug = (...args) => {
      this.originalConsole.debug(...args);
      this.addLog('DEBUG', args);
    };
  }

  addLog(level, args) {
    const timestamp = new Date().toISOString();
    const message = args.map(arg => 
      typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
    ).join(' ');

    const logEntry = {
      timestamp,
      level,
      message,
      url: window.location.href,
      userAgent: navigator.userAgent
    };

    this.logBuffer.push(logEntry);

    // Flush buffer if it's getting full
    if (this.logBuffer.length >= this.maxBufferSize) {
      this.flushLogs();
    }
  }

  async flushLogs() {
    if (this.logBuffer.length === 0) return;

    const logsToSend = [...this.logBuffer];
    this.logBuffer = [];

    try {
      await fetch(this.logEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs: logsToSend,
          source: 'frontend'
        })
      });
    } catch (error) {
      // Restore logs to buffer if send failed
      this.logBuffer.unshift(...logsToSend);
      this.originalConsole.error('Failed to send frontend logs to backend:', error);
    }
  }

  setupAutoFlush() {
    // Auto-flush every 5 seconds
    setInterval(() => {
      this.flushLogs();
    }, this.flushInterval);

    // Flush on page unload
    window.addEventListener('beforeunload', () => {
      this.flushLogs();
    });
  }

  // Manual logging methods for structured logging
  logWorkflow(action, data) {
    console.log(`🔧 WORKFLOW_${action.toUpperCase()}:`, data);
  }

  logAPI(method, url, data, response) {
    console.log(`🌐 API_${method.toUpperCase()}: ${url}`, { data, response });
  }

  logError(context, error) {
    console.error(`❌ ERROR_${context.toUpperCase()}:`, error);
  }

  logDebug(context, data) {
    console.debug(`🔍 DEBUG_${context.toUpperCase()}:`, data);
  }
}

// Create global instance
const frontendLogger = new FrontendLogger();

// Export for manual use
export default frontendLogger;