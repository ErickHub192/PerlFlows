import { useState } from 'preact/hooks';

export function WebhookBanner({ webhookUrls, onClose }) {
  const [copiedUrl, setCopiedUrl] = useState(null);

  const copyToClipboard = async (url, type) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedUrl(type);
      setTimeout(() => setCopiedUrl(null), 2000);
    } catch (err) {
      console.error('Failed to copy URL:', err);
    }
  };

  const testWebhook = async (url) => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          test: true,
          name: 'Test User',
          email: 'test@example.com',
          timestamp: new Date().toISOString()
        })
      });
      
      if (response.ok) {
        alert('✅ Webhook test successful!');
      } else {
        alert('❌ Webhook test failed. Check console for details.');
      }
    } catch (error) {
      console.error('Webhook test error:', error);
      alert('❌ Webhook test failed. Check console for details.');
    }
  };

  if (!webhookUrls) return null;

  return (
    <div className="webhook-banner">
      <div className="webhook-banner-content">
        <div className="webhook-banner-header">
          <span className="webhook-icon">🌐</span>
          <h3>Webhook URLs for this workflow</h3>
          <button 
            className="close-button"
            onClick={onClose}
            title="Close banner"
          >
            ×
          </button>
        </div>
        
        <div className="webhook-urls">
          <div className="webhook-url-item">
            <span className="url-label">Test:</span>
            <span className="url-text">{webhookUrls.test}</span>
            <div className="url-actions">
              <button
                className={`copy-button ${copiedUrl === 'test' ? 'copied' : ''}`}
                onClick={() => copyToClipboard(webhookUrls.test, 'test')}
                title="Copy test URL"
              >
                {copiedUrl === 'test' ? '✓ Copied' : 'Copy'}
              </button>
              <button
                className="test-button"
                onClick={() => testWebhook(webhookUrls.test)}
                title="Test this webhook"
              >
                Test Now
              </button>
            </div>
          </div>
          
          <div className="webhook-url-item">
            <span className="url-label">Production:</span>
            <span className="url-text">{webhookUrls.production}</span>
            <div className="url-actions">
              <button
                className={`copy-button ${copiedUrl === 'production' ? 'copied' : ''}`}
                onClick={() => copyToClipboard(webhookUrls.production, 'production')}
                title="Copy production URL"
              >
                {copiedUrl === 'production' ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        .webhook-banner {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 16px;
          margin-bottom: 16px;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .webhook-banner-content {
          max-width: 100%;
        }
        
        .webhook-banner-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }
        
        .webhook-icon {
          font-size: 20px;
        }
        
        .webhook-banner-header h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          flex: 1;
        }
        
        .close-button {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          cursor: pointer;
          font-size: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s;
        }
        
        .close-button:hover {
          background: rgba(255, 255, 255, 0.3);
        }
        
        .webhook-urls {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .webhook-url-item {
          display: flex;
          align-items: center;
          gap: 12px;
          background: rgba(255, 255, 255, 0.1);
          padding: 12px;
          border-radius: 8px;
          backdrop-filter: blur(5px);
        }
        
        .url-label {
          font-weight: 600;
          min-width: 80px;
          font-size: 14px;
        }
        
        .url-text {
          flex: 1;
          font-family: 'Courier New', monospace;
          font-size: 13px;
          background: rgba(0, 0, 0, 0.2);
          padding: 8px 12px;
          border-radius: 6px;
          word-break: break-all;
        }
        
        .url-actions {
          display: flex;
          gap: 8px;
        }
        
        .copy-button, .test-button {
          background: rgba(255, 255, 255, 0.2);
          border: 1px solid rgba(255, 255, 255, 0.3);
          color: white;
          padding: 6px 12px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          transition: all 0.2s;
          white-space: nowrap;
        }
        
        .copy-button:hover, .test-button:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: translateY(-1px);
        }
        
        .copy-button.copied {
          background: rgba(34, 197, 94, 0.8);
          border-color: rgba(34, 197, 94, 1);
        }
        
        .test-button {
          background: rgba(59, 130, 246, 0.8);
          border-color: rgba(59, 130, 246, 1);
        }
        
        .test-button:hover {
          background: rgba(59, 130, 246, 1);
        }
        
        @media (max-width: 768px) {
          .webhook-url-item {
            flex-direction: column;
            align-items: stretch;
            gap: 8px;
          }
          
          .url-actions {
            justify-content: center;
          }
          
          .url-label {
            min-width: unset;
            text-align: center;
          }
        }
      `}</style>
    </div>
  );
}