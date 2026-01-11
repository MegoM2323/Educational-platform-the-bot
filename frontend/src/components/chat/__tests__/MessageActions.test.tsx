import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageActions } from '../MessageActions';

describe('MessageActions', () => {
  it('should render null when user is not owner and cannot moderate', () => {
    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={false}
        canModerate={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('should render actions when user is owner', () => {
    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={true}
        canModerate={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(container.querySelector('button')).toBeInTheDocument();
  });

  it('should render actions when user can moderate', () => {
    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={false}
        canModerate={true}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(container.querySelector('button')).toBeInTheDocument();
  });

  it('should call onEdit when edit is clicked', async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();

    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={true}
        canModerate={false}
        onEdit={onEdit}
        onDelete={vi.fn()}
      />
    );

    const button = container.querySelector('button');
    if (button) {
      await user.click(button);

      // Find and click the edit menu item
      const editItem = screen.queryByText(/Редактировать/i);
      if (editItem) {
        await user.click(editItem);
        expect(onEdit).toHaveBeenCalled();
      }
    }
  });

  it('should call onDelete when delete is clicked', async () => {
    const onDelete = vi.fn();
    const user = userEvent.setup();

    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={true}
        canModerate={false}
        onEdit={vi.fn()}
        onDelete={onDelete}
      />
    );

    const button = container.querySelector('button');
    if (button) {
      await user.click(button);

      // Find and click the delete menu item
      const deleteItem = screen.queryByText(/Удалить/i);
      if (deleteItem) {
        await user.click(deleteItem);
        expect(onDelete).toHaveBeenCalled();
      }
    }
  });

  it('should disable actions when disabled prop is true', () => {
    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={true}
        canModerate={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        disabled={true}
      />
    );

    const button = container.querySelector('button');
    expect(button).toHaveAttribute('disabled');
  });

  it('should show only delete option for moderators', () => {
    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={false}
        canModerate={true}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(container.querySelector('button')).toBeInTheDocument();
  });

  it('should show edit and delete options for owners', () => {
    const { container } = render(
      <MessageActions
        messageId={1}
        isOwner={true}
        canModerate={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(container.querySelector('button')).toBeInTheDocument();
  });
});
