import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AvatarUpload } from '../AvatarUpload';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('AvatarUpload', () => {
  const mockOnAvatarUpload = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен отобразить компонент с инициалами', () => {
    render(
      <AvatarUpload
        onAvatarUpload={mockOnAvatarUpload}
        fallbackInitials="АА"
      />
    );

    expect(screen.getByText('АА')).toBeInTheDocument();
  });

  it('должен отобразить текущий аватар если передан', () => {
    const avatarUrl = 'https://example.com/avatar.jpg';
    render(
      <AvatarUpload
        currentAvatar={avatarUrl}
        onAvatarUpload={mockOnAvatarUpload}
      />
    );

    const img = screen.getByAltText('Аватар');
    expect(img).toHaveAttribute('src', avatarUrl);
  });

  it('должен отобразить зону для перетаскивания', () => {
    render(<AvatarUpload onAvatarUpload={mockOnAvatarUpload} />);

    expect(
      screen.getByText(/Перетащите изображение сюда/i)
    ).toBeInTheDocument();
  });

  it('должен отобразить информацию о форматах', () => {
    render(<AvatarUpload onAvatarUpload={mockOnAvatarUpload} />);

    expect(screen.getByText(/JPG, PNG, WebP/i)).toBeInTheDocument();
  });

  it('должен отключить input при loading=true', () => {
    render(
      <AvatarUpload
        onAvatarUpload={mockOnAvatarUpload}
        isLoading={true}
      />
    );

    const input = screen.getByLabelText('Выбор файла аватара') as HTMLInputElement;
    expect(input).toBeDisabled();
  });

  it('должен показать "Загрузка..." при loading=true', () => {
    render(
      <AvatarUpload
        onAvatarUpload={mockOnAvatarUpload}
        isLoading={true}
      />
    );

    expect(screen.getByText('Загрузка...')).toBeInTheDocument();
  });

  it('должен иметь правильные aria-label', () => {
    render(<AvatarUpload onAvatarUpload={mockOnAvatarUpload} />);

    expect(screen.getByLabelText('Зона для загрузки изображения')).toBeInTheDocument();
    expect(screen.getByLabelText('Загрузить аватар')).toBeInTheDocument();
    expect(screen.getByLabelText('Выбор файла аватара')).toBeInTheDocument();
  });
});
