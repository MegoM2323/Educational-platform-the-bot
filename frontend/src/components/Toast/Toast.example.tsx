import React, { useState } from 'react';
import { Toast, ToastContainer } from './index';
import { Button } from '@/components/ui/button';

/**
 * Example: Using Toast components directly
 */
export const ToastDirectExample = () => {
  const [toasts, setToasts] = useState([
    {
      id: '1',
      type: 'success' as const,
      title: 'Success Message',
      description: 'This is a success notification',
    },
  ]);

  const handleRemove = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold mb-4">Direct Toast Usage</h3>
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            id={toast.id}
            type={toast.type}
            title={toast.title}
            description={toast.description}
            onClose={handleRemove}
          />
        ))}
      </div>
    </div>
  );
};

/**
 * Example: Using Toast types and auto-dismiss
 */
export const ToastTypesExample = () => {
  const [toasts, setToasts] = useState([
    {
      id: '1',
      type: 'success' as const,
      title: 'Success',
      description: 'Changes have been saved',
      duration: 3000,
    },
    {
      id: '2',
      type: 'error' as const,
      title: 'Error',
      description: 'Something went wrong',
      duration: 5000,
    },
    {
      id: '3',
      type: 'warning' as const,
      title: 'Warning',
      description: 'Please review your input',
      duration: 4000,
    },
    {
      id: '4',
      type: 'info' as const,
      title: 'Information',
      description: 'Update available',
      duration: 3000,
    },
    {
      id: '5',
      type: 'loading' as const,
      title: 'Processing your request...',
    },
  ]);

  const handleRemove = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="p-8 bg-gray-50 rounded-lg">
      <h3 className="font-semibold mb-6">Toast Types</h3>
      <div className="space-y-3">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            id={toast.id}
            type={toast.type}
            title={toast.title}
            description={toast.description}
            duration={toast.duration}
            onClose={handleRemove}
          />
        ))}
      </div>
    </div>
  );
};

/**
 * Example: Toast with action button
 */
export const ToastWithActionExample = () => {
  const [toasts, setToasts] = useState([
    {
      id: '1',
      type: 'success' as const,
      title: 'Item saved',
      description: 'Your changes have been successfully saved.',
      action: {
        label: 'Undo',
        onClick: () => alert('Undo action clicked'),
      },
    },
    {
      id: '2',
      type: 'error' as const,
      title: 'Failed to save',
      description: 'Could not save your changes.',
      action: {
        label: 'Retry',
        onClick: () => alert('Retry action clicked'),
      },
    },
  ]);

  const handleRemove = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="p-8 bg-gray-50 rounded-lg">
      <h3 className="font-semibold mb-6">Toast with Actions</h3>
      <div className="space-y-3">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            id={toast.id}
            type={toast.type}
            title={toast.title}
            description={toast.description}
            action={toast.action}
            onClose={handleRemove}
          />
        ))}
      </div>
    </div>
  );
};

/**
 * Example: Toast container with multiple toasts
 */
export const ToastContainerExample = () => {
  const [toasts, setToasts] = useState([
    {
      id: '1',
      type: 'success' as const,
      title: 'First notification',
      description: 'This appears first',
    },
    {
      id: '2',
      type: 'info' as const,
      title: 'Second notification',
      description: 'This appears second',
    },
  ]);

  const [position, setPosition] = useState<
    'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
  >('top-right');

  const handleRemove = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleAddToast = () => {
    const id = String(Date.now());
    setToasts((prev) => [
      ...prev,
      {
        id,
        type: 'info' as const,
        title: 'New notification',
        description: `Added at ${new Date().toLocaleTimeString()}`,
      },
    ]);
  };

  return (
    <div className="p-8 bg-gray-50 rounded-lg">
      <h3 className="font-semibold mb-6">Toast Container Example</h3>

      <div className="mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Position:</label>
          <div className="flex gap-2 flex-wrap">
            {['top-right', 'top-left', 'bottom-right', 'bottom-left'].map(
              (pos) => (
                <button
                  key={pos}
                  onClick={() =>
                    setPosition(
                      pos as 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
                    )
                  }
                  className={`px-3 py-1 rounded text-sm ${
                    position === pos
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-300'
                  }`}
                >
                  {pos}
                </button>
              )
            )}
          </div>
        </div>

        <Button onClick={handleAddToast}>Add Toast</Button>
      </div>

      <div className="relative h-40 border-2 border-dashed border-gray-300 rounded-lg">
        <ToastContainer
          toasts={toasts}
          onRemove={handleRemove}
          position={position}
        />
      </div>
    </div>
  );
};

/**
 * Main example component
 */
export const ToastExamples = () => {
  return (
    <div className="space-y-8 p-8">
      <section>
        <h2 className="text-2xl font-bold mb-4">Toast Component Examples</h2>
      </section>

      <section>
        <h3 className="text-lg font-semibold mb-4">Toast Types</h3>
        <ToastTypesExample />
      </section>

      <section>
        <h3 className="text-lg font-semibold mb-4">Toast with Action</h3>
        <ToastWithActionExample />
      </section>

      <section>
        <h3 className="text-lg font-semibold mb-4">Toast Container</h3>
        <ToastContainerExample />
      </section>

      <section>
        <h3 className="text-lg font-semibold mb-4">Direct Usage</h3>
        <ToastDirectExample />
      </section>
    </div>
  );
};
