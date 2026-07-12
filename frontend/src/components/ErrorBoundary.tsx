/**
 * Error boundary — catches React render errors and shows a recovery UI.
 */

import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[NetworkGlobe] Render error:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          width: '100vw',
          background: '#0a0e1a',
          color: '#f1f5f9',
          fontFamily: 'Inter, sans-serif',
          padding: '40px',
          textAlign: 'center',
        }}>
          <div style={{
            background: 'rgba(17, 25, 40, 0.75)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '40px',
            maxWidth: '480px',
            width: '100%',
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
            <h1 style={{
              fontSize: '20px',
              fontWeight: 700,
              marginBottom: '12px',
              background: 'linear-gradient(135deg, #818cf8, #22d3ee)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              Something went wrong
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '20px', lineHeight: 1.5 }}>
              NetworkGlobe encountered an unexpected error. This is usually temporary.
            </p>
            <pre style={{
              background: '#1e293b',
              borderRadius: '8px',
              padding: '12px',
              fontSize: '11px',
              color: '#ef4444',
              textAlign: 'left',
              overflow: 'auto',
              maxHeight: '120px',
              marginBottom: '20px',
              fontFamily: 'JetBrains Mono, monospace',
            }}>
              {this.state.error?.message || 'Unknown error'}
            </pre>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '10px 24px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'Inter, sans-serif',
              }}
            >
              Reload Dashboard
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
