import { render, screen, fireEvent } from '@testing-library/preact';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import ErrorBoundary from '../ErrorBoundary';
import { TestErrorComponent } from '@/test/mocks/api';

// Mock console.error to avoid noise in tests
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('renders error fallback when child component throws', () => {
    render(
      <ErrorBoundary>
        <TestErrorComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Algo salió mal')).toBeInTheDocument();
    expect(screen.getByText(/Ha ocurrido un error inesperado/)).toBeInTheDocument();
  });

  it('shows retry button and handles retry action', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <TestErrorComponent />
      </ErrorBoundary>
    );

    // Error should be displayed
    expect(screen.getByText('Algo salió mal')).toBeInTheDocument();
    
    // Retry button should be present
    const retryButton = screen.getByText('Intentar de nuevo');
    expect(retryButton).toBeInTheDocument();

    // Mock a working component for retry
    const WorkingComponent = () => <div>Component working</div>;
    
    // Click retry button
    fireEvent.click(retryButton);
    
    // Re-render with working component
    rerender(
      <ErrorBoundary>
        <WorkingComponent />
      </ErrorBoundary>
    );

    // Should show the working component
    expect(screen.getByText('Component working')).toBeInTheDocument();
  });

  it('renders custom fallback component when provided', () => {
    const CustomFallback = ({ error, retry }: { error: Error; retry: () => void }) => (
      <div>
        <h2>Custom Error</h2>
        <p>Error: {error.message}</p>
        <button onClick={retry}>Custom Retry</button>
      </div>
    );

    render(
      <ErrorBoundary fallback={CustomFallback}>
        <TestErrorComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom Error')).toBeInTheDocument();
    expect(screen.getByText('Error: Test error')).toBeInTheDocument();
    expect(screen.getByText('Custom Retry')).toBeInTheDocument();
  });

  it('logs error to console when error occurs', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <TestErrorComponent />
      </ErrorBoundary>
    );

    expect(consoleSpy).toHaveBeenCalledWith(
      'ErrorBoundary caught an error:',
      expect.any(Error),
      expect.any(Object)
    );

    consoleSpy.mockRestore();
  });

  it('resets error state on successful retry', () => {
    let shouldThrow = true;
    
    const ConditionalComponent = () => {
      if (shouldThrow) {
        throw new Error('Conditional error');
      }
      return <div>Success!</div>;
    };

    const { rerender } = render(
      <ErrorBoundary>
        <ConditionalComponent />
      </ErrorBoundary>
    );

    // Should show error initially
    expect(screen.getByText('Algo salió mal')).toBeInTheDocument();

    // Change condition and retry
    shouldThrow = false;
    const retryButton = screen.getByText('Intentar de nuevo');
    fireEvent.click(retryButton);

    rerender(
      <ErrorBoundary>
        <ConditionalComponent />
      </ErrorBoundary>
    );

    // Should show success content
    expect(screen.getByText('Success!')).toBeInTheDocument();
  });

  it('handles multiple sequential errors', () => {
    let errorMessage = 'First error';
    
    const DynamicErrorComponent = () => {
      throw new Error(errorMessage);
    };

    const { rerender } = render(
      <ErrorBoundary>
        <DynamicErrorComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Algo salió mal')).toBeInTheDocument();

    // Change error message and trigger new error
    errorMessage = 'Second error';
    const retryButton = screen.getByText('Intentar de nuevo');
    fireEvent.click(retryButton);

    rerender(
      <ErrorBoundary>
        <DynamicErrorComponent />
      </ErrorBoundary>
    );

    // Should still show error boundary (with new error)
    expect(screen.getByText('Algo salió mal')).toBeInTheDocument();
  });
});