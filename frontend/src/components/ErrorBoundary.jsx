import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled rendering error:', error, errorInfo);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#080b11] text-gray-100 flex items-center justify-center p-6">
          <div className="max-w-md w-full p-8 rounded-2xl bg-gray-950 border border-red-800/60 shadow-2xl text-center space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full bg-red-950/60 border border-red-800/80 flex items-center justify-center text-red-400">
              <AlertOctagon className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-white font-mono">Live Dashboard Interface Recovered</h2>
            <p className="text-xs text-gray-400 font-mono">
              A temporary display glitch was intercepted: {this.state.error?.message || 'State parsing error'}.
            </p>
            <button
              onClick={this.handleReload}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors font-mono shadow-lg shadow-blue-600/30"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Resume Live Monitor</span>
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
