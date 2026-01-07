import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ParentSidebar } from '../ParentSidebar'

const mockSignOut = vi.fn()
const mockUseSidebar = vi.fn()
const mockInvoiceAPI = vi.fn()

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    signOut: mockSignOut,
    user: { id: 1, role: 'parent' }
  })
}))

vi.mock('@/components/ui/sidebar', async () => {
  const actual = await vi.importActual('@/components/ui/sidebar')
  return {
    ...actual,
    useSidebar: () => mockUseSidebar()
  }
})

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query')
  return {
    ...actual,
    useQuery: (config: any) => {
      if (config.queryKey[0] === 'parent-invoices-unpaid-count') {
        return { data: 2, isLoading: false }
      }
      return actual.useQuery(config)
    }
  }
})

vi.mock('@/components/chat/ChatNotificationBadge', () => ({
  ChatNotificationBadge: () => <div data-testid="chat-badge">Chat Badge</div>
}))

describe('ParentSidebar', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()
    mockUseSidebar.mockReturnValue({ state: 'expanded' })
  })

  it('should render sidebar with navigation items', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Главная')).toBeInTheDocument()
    expect(screen.getByText('Мои дети')).toBeInTheDocument()
    expect(screen.getByText('История платежей')).toBeInTheDocument()
  })

  it('should render all menu items', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Счета')).toBeInTheDocument()
    expect(screen.getByText('Статистика')).toBeInTheDocument()
    expect(screen.getByText('Отчёты')).toBeInTheDocument()
    expect(screen.getByText('Форум')).toBeInTheDocument()
    expect(screen.getByText('Сообщения')).toBeInTheDocument()
  })

  it('should render profile link in footer', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Профиль')).toBeInTheDocument()
  })

  it('should render logout button', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Выход')).toBeInTheDocument()
  })

  it('should handle logout click', async () => {
    const user = userEvent.setup()

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    const logoutButton = screen.getByText('Выход')
    await user.click(logoutButton)

    expect(mockSignOut).toHaveBeenCalled()
  })

  it('should display unpaid invoices badge', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  it('should render collapsed state', () => {
    mockUseSidebar.mockReturnValue({ state: 'collapsed' })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.queryByText('Главная')).not.toBeInTheDocument()
  })

  it('should display chat notification badge', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ParentSidebar />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByTestId('chat-badge')).toBeInTheDocument()
  })
})
