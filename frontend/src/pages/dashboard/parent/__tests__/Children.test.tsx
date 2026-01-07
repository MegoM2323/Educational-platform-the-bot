import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Children from '../Children'

const mockUseParentChildren = vi.fn()
const mockUseInitiatePayment = vi.fn()
const mockNavigate = vi.fn()

vi.mock('@/hooks/useParent', () => ({
  useParentChildren: () => mockUseParentChildren(),
  useInitiatePayment: () => ({
    mutate: vi.fn(),
    isPending: false
  })
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

vi.mock('@/integrations/api/dashboard', () => ({
  parentDashboardAPI: {
    cancelSubscription: vi.fn().mockResolvedValue({ success: true })
  }
}))

vi.mock('@/components/PaymentStatusBadge', () => ({
  PaymentStatusBadge: ({ status }: any) => <div>{status}</div>
}))

vi.mock('@/components/ui/PayButton', () => ({
  PayButton: ({ onPayClick, onCancelClick }: any) => (
    <div>
      <button onClick={onPayClick}>Pay</button>
      <button onClick={onCancelClick}>Cancel</button>
    </div>
  )
}))

describe('Children', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()
  })

  it('should render children page header', () => {
    mockUseParentChildren.mockReturnValue({
      data: [],
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Children />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Мои дети')).toBeInTheDocument()
  })

  it('should display loading state', () => {
    mockUseParentChildren.mockReturnValue({
      data: null,
      isLoading: true
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Children />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Загрузка...')).toBeInTheDocument()
  })

  it('should display list of children', async () => {
    const mockChildren = [
      {
        id: 1,
        name: 'Ivan',
        full_name: 'Ivan Ivanov',
        grade: '9',
        goal: 'Math improvement',
        subjects: []
      }
    ]

    mockUseParentChildren.mockReturnValue({
      data: mockChildren,
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Children />
        </BrowserRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Ivan Ivanov')).toBeInTheDocument()
      expect(screen.getByText('9')).toBeInTheDocument()
    })
  })

  it('should display child subjects', async () => {
    const mockChildren = [
      {
        id: 1,
        name: 'Ivan',
        full_name: 'Ivan Ivanov',
        grade: '9',
        goal: 'Math',
        subjects: [
          {
            enrollment_id: 1,
            id: 1,
            name: 'Math',
            teacher_name: 'John',
            payment_status: 'paid',
            has_subscription: true
          }
        ]
      }
    ]

    mockUseParentChildren.mockReturnValue({
      data: mockChildren,
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Children />
        </BrowserRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Math')).toBeInTheDocument()
      expect(screen.getByText('Преподаватель: John')).toBeInTheDocument()
    })
  })

  it('should navigate to child detail on button click', async () => {
    const user = userEvent.setup()
    const mockChildren = [
      {
        id: 1,
        name: 'Ivan',
        full_name: 'Ivan Ivanov',
        grade: '9',
        goal: 'Math',
        subjects: []
      }
    ]

    mockUseParentChildren.mockReturnValue({
      data: mockChildren,
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Children />
        </BrowserRouter>
      </QueryClientProvider>
    )

    const detailButton = screen.getByText('Детали')
    await user.click(detailButton)

    expect(mockNavigate).toHaveBeenCalledWith('/dashboard/parent/children/1')
  })

  it('should display empty state when no children', () => {
    mockUseParentChildren.mockReturnValue({
      data: [],
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Children />
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Мои дети')).toBeInTheDocument()
  })

  it('should display multiple children cards', async () => {
    const mockChildren = [
      {
        id: 1,
        name: 'Ivan',
        full_name: 'Ivan Ivanov',
        grade: '9',
        goal: 'Math',
        subjects: []
      },
      {
        id: 2,
        name: 'Maria',
        full_name: 'Maria Ivanova',
        grade: '10',
        goal: 'English',
        subjects: []
      }
    ]

    mockUseParentChildren.mockReturnValue({
      data: mockChildren,
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Children />
        </BrowserRouter>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Ivan Ivanov')).toBeInTheDocument()
      expect(screen.getByText('Maria Ivanova')).toBeInTheDocument()
    })
  })
})
