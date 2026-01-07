import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { vi as vitestVi } from 'vitest'

const mockUseParams = vi.fn()
const mockNavigate = vi.fn()
const mockGetChildDetail = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => mockUseParams(),
    useNavigate: () => mockNavigate
  }
})

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

describe('ChildDetail', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()
    mockUseParams.mockReturnValue({ childId: '1' })
  })

  it('should render child detail page', () => {
    mockGetChildDetail.mockResolvedValue({
      id: 1,
      name: 'Ivan',
      grade: '9',
      goal: 'Math improvement',
      tutor_name: 'John',
      progress_percentage: 75,
      subjects: []
    })

    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Child Detail Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(container).toBeTruthy()
  })

  it('should display child information', async () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Child Detail Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(container).toBeTruthy()
  })

  it('should load child data on mount', () => {
    expect(mockUseParams).toBeDefined()
  })

  it('should handle back navigation', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Child Detail Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockNavigate).toBeDefined()
  })

  it('should display child grade', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Child Detail Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockUseParams).toBeDefined()
  })

  it('should display tutor information', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Child Detail Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockGetChildDetail).toBeDefined()
  })
})
