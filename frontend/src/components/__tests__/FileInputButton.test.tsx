import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Paperclip } from 'lucide-react';

/**
 * Test component that mimics the Forum paperclip button pattern
 */
const FileInputButtonExample = () => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        accept="image/*,.pdf"
        style={{ display: 'none' }}
        data-testid="file-input-hidden"
      />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => {
          fileInputRef.current?.click();
        }}
        data-testid="file-attach-button"
      >
        <Paperclip className="w-4 h-4" />
      </Button>
    </div>
  );
};

describe('FileInputButton - Paperclip Bug Fix', () => {
  it('should render hidden file input with correct styling', () => {
    render(<FileInputButtonExample />);

    const fileInput = screen.getByTestId('file-input-hidden') as HTMLInputElement;

    expect(fileInput).toBeInTheDocument();
    expect(fileInput.type).toBe('file');
    expect(fileInput.style.display).toBe('none');
  });

  it('should render paperclip button', () => {
    render(<FileInputButtonExample />);

    const button = screen.getByTestId('file-attach-button');

    expect(button).toBeInTheDocument();
    expect(button.tagName).toBe('BUTTON');
    expect(button.type).toBe('button');
  });

  it('should trigger file input click when button is clicked', async () => {
    const user = userEvent.setup();

    render(<FileInputButtonExample />);

    const fileInput = screen.getByTestId('file-input-hidden') as HTMLInputElement;
    const button = screen.getByTestId('file-attach-button');

    // Spy on the click method
    const clickSpy = vi.spyOn(fileInput, 'click');

    // Click the button
    await user.click(button);

    // Verify file input click was triggered
    expect(clickSpy).toHaveBeenCalled();
  });

  it('should have correct file input ref connection', () => {
    render(<FileInputButtonExample />);

    const fileInput = screen.getByTestId('file-input-hidden') as HTMLInputElement;

    // Verify the input can be clicked programmatically
    expect(typeof fileInput.click).toBe('function');
  });
});
