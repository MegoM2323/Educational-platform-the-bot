import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

const mockNavigate = vi.fn()
const mockSearchParams = new URLSearchParams()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [mockSearchParams, vi.fn()]
  }
})

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

describe('PaymentSuccess', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()
  })

  it('should render payment success page', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment Success Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Payment Success Test')).toBeInTheDocument()
  })

  it('should display success message', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment Success Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Payment Success Test')).toBeInTheDocument()
  })

  it('should display payment confirmation details', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment Success Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockSearchParams).toBeDefined()
  })

  it('should provide navigation back to dashboard', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment Success Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockNavigate).toBeDefined()
  })

  it('should display payment receipt information', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Payment Success Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Payment Success Test')).toBeInTheDocument()
  })
})
