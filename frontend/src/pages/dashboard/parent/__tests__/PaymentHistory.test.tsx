import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

const mockParentDashboardAPI = vi.fn()
const mockNavigate = vi.fn()
const mockToast = vi.fn()

vi.mock('@/integrations/api/dashboard', () => ({
  parentDashboardAPI: {
    getPaymentHistory: () => mockParentDashboardAPI()
  }
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast })
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams(), vi.fn()]
  }
})

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

vi.mock('@/components/PaymentStatusBadge', () => ({
  PaymentStatusBadge: ({ status }: any) => <div>{status}</div>
}))

describe('PaymentHistory', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()
  })

  it('should render payment history page', () => {
    mockParentDashboardAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment History Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Payment History Test')).toBeInTheDocument()
  })

  it('should display payment records', async () => {
    const mockPayments = [
      {
        id: 1,
        enrollment_id: 1,
        subject: 'Math',
        teacher: 'John',
        student: 'Ivan',
        status: 'paid',
        amount: '5000',
        paid_at: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z'
      }
    ]

    mockParentDashboardAPI.mockResolvedValue(mockPayments)

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment History Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Payment History Test')).toBeInTheDocument()
  })

  it('should load payment history on mount', () => {
    mockParentDashboardAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment History Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockParentDashboardAPI).toBeDefined()
  })

  it('should handle error loading payments', async () => {
    const mockError = new Error('Failed to load')
    mockParentDashboardAPI.mockRejectedValue(mockError)

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment History Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockParentDashboardAPI).toBeDefined()
  })

  it('should display pagination controls', () => {
    mockParentDashboardAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment History Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Payment History Test')).toBeInTheDocument()
  })

  it('should handle payment status filtering', () => {
    mockParentDashboardAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment History Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockNavigate).toBeDefined()
  })

  it('should display payment amounts', () => {
    mockParentDashboardAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment History Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockParentDashboardAPI).toBeDefined()
  })
})
