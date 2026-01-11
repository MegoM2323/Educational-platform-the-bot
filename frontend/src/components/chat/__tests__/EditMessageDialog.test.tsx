import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditMessageDialog } from '../EditMessageDialog';

describe('EditMessageDialog', () => {
  it('should render dialog when isOpen is true', () => {
    render(
      <EditMessageDialog
        isOpen={true}
        onClose={vi.fn()}
        messageContent="Test content"
        onSave={vi.fn()}
      />
    );

    expect(screen.getByText(/Редактировать сообщение/i)).toBeInTheDocument();
  });

  it('should not render dialog when isOpen is false', () => {
    const { container } = render(
      <EditMessageDialog
        isOpen={false}
        onClose={vi.fn()}
        messageContent="Test content"
        onSave={vi.fn()}
      />
    );

    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it('should display current message content', () => {
    render(
      <EditMessageDialog
        isOpen={true}
        onClose={vi.fn()}
        messageContent="Original message"
        onSave={vi.fn()}
      />
    );

    const textarea = screen.getByPlaceholderText(/Введите сообщение/i) as HTMLTextAreaElement;
    expect(textarea.value).toBe('Original message');
  });

  it('should call onSave when save button is clicked', async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();

    render(
      <EditMessageDialog
        isOpen={true}
        onClose={vi.fn()}
        messageContent="Original"
        onSave={onSave}
      />
    );

    const textarea = screen.getByPlaceholderText(/Введите сообщение/i);
    await user.clear(textarea);
    await user.type(textarea, 'Updated content');

    const saveButton = screen.getByText(/^Сохранить$/i);
    await user.click(saveButton);

    expect(onSave).toHaveBeenCalledWith('Updated content');
  });

  it('should call onClose when cancel button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <EditMessageDialog
        isOpen={true}
        onClose={onClose}
        messageContent="Original"
        onSave={vi.fn()}
      />
    );

    const cancelButton = screen.getByText(/Отмена/i);
    await user.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('should validate empty content', async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();

    render(
      <EditMessageDialog
        isOpen={true}
        onClose={vi.fn()}
        messageContent="Original"
        onSave={onSave}
      />
    );

    const textarea = screen.getByPlaceholderText(/Введите сообщение/i);
    await user.clear(textarea);

    const saveButton = screen.getByText(/^Сохранить$/i);
    await user.click(saveButton);

    expect(screen.getByText(/Сообщение не может быть пустым/i)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });


  it('should show loading state when isLoading is true', () => {
    render(
      <EditMessageDialog
        isOpen={true}
        onClose={vi.fn()}
        messageContent="Original"
        onSave={vi.fn()}
        isLoading={true}
      />
    );

    expect(screen.getByText(/Сохранение/i)).toBeInTheDocument();
  });

  it('should display character count', () => {
    render(
      <EditMessageDialog
        isOpen={true}
        onClose={vi.fn()}
        messageContent="Test"
        onSave={vi.fn()}
      />
    );

    expect(screen.getByText(/4\/5000 символов/i)).toBeInTheDocument();
  });
});
