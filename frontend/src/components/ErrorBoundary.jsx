import { Component } from 'react';

/**
 * Global React error boundary.
 * Catches any unhandled JS error in the component tree and renders
 * a recoverable error card instead of a blank screen.
 *
 * Usage (in App.jsx):
 *   <ErrorBoundary>
 *     <App />
 *   </ErrorBoundary>
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[MacroPulse] Unhandled render error:', error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div style={{
        minHeight: '100vh',
        background: '#0a0a0a',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 32,
      }}>
        <div style={{
          background: '#111',
          border: '1px solid rgba(239,68,68,0.25)',
          borderRadius: 10,
          padding: '32px 40px',
          maxWidth: 480,
          fontFamily: 'JetBrains Mono, monospace',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 11, color: '#ef4444', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 12 }}>
            render error
          </div>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', lineHeight: 1.6, marginBottom: 20 }}>
            Something went wrong loading this view.
          </div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', marginBottom: 24, wordBreak: 'break-all' }}>
            {this.state.error?.message}
          </div>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: 6,
              color: 'rgba(255,255,255,0.5)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              padding: '6px 16px',
              cursor: 'pointer',
            }}
          >
            try again
          </button>
        </div>
      </div>
    );
  }
}
