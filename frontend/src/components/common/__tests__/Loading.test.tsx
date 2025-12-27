import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Spinner,
  LoadingState,
  Skeleton,
  TextLineSkeleton,
  ParagraphSkeleton,
  CardSkeleton,
  TableSkeleton,
  ListSkeleton,
  FormSkeleton,
  GridSkeleton,
  ProgressBar,
  LoadingOverlay,
  ShimmerSkeleton,
  PulseSkeleton,
  SkeletonWrapper,
} from '../Loading';

// ============================================================================
// TEST SETUP
// ============================================================================

describe('Loading Components', () => {
  // ========================================================================
  // SPINNER TESTS
  // ========================================================================

  describe('Spinner', () => {
    it('should render spinner with default size', () => {
      const { container } = render(<Spinner />);
      const icon = container.querySelector('[class*="animate-spin"]');
      expect(icon).toBeInTheDocument();
    });

    it('should render spinner with custom size', () => {
      const { container } = render(<Spinner size="lg" />);
      const icon = container.querySelector('svg');
      expect(icon).toHaveClass('w-8', 'h-8');
    });

    it('should have correct aria attributes', () => {
      const { container } = render(<Spinner ariaLabel="Loading data..." />);
      const status = container.querySelector('[role="status"]');
      expect(status).toHaveAttribute('aria-label', 'Loading data...');
      expect(status).toHaveAttribute('aria-live', 'polite');
    });

    it('should support all size variants', () => {
      const sizes = ['xs', 'sm', 'md', 'lg', 'xl'] as const;
      sizes.forEach(size => {
        const { container } = render(<Spinner size={size} />);
        const icon = container.querySelector('svg');
        expect(icon).toBeInTheDocument();
      });
    });

    it('should apply custom className', () => {
      const { container } = render(<Spinner className="text-red-500" />);
      const icon = container.querySelector('svg');
      expect(icon).toHaveClass('text-red-500');
    });
  });

  // ========================================================================
  // LOADING STATE TESTS
  // ========================================================================

  describe('LoadingState', () => {
    it('should not render when isLoading is false', () => {
      const { container } = render(<LoadingState isLoading={false} />);
      expect(container.querySelector('[role="status"]')).not.toBeInTheDocument();
    });

    it('should render when isLoading is true', () => {
      const { container } = render(<LoadingState isLoading={true} />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });

    it('should display loading text', () => {
      render(<LoadingState isLoading={true} text="Loading content..." />);
      expect(screen.getByText('Loading content...')).toBeInTheDocument();
    });

    it('should apply fullHeight class when specified', () => {
      const { container } = render(<LoadingState isLoading={true} fullHeight />);
      const status = container.querySelector('[role="status"]');
      expect(status).toHaveClass('h-screen');
    });

    it('should render spinner with custom size', () => {
      const { container } = render(<LoadingState isLoading={true} size="lg" />);
      const icon = container.querySelector('svg');
      expect(icon).toHaveClass('w-8', 'h-8');
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(
        <LoadingState isLoading={true} ariaLabel="Loading user data..." />
      );
      const status = container.querySelector('[role="status"]');
      expect(status).toHaveAttribute('aria-label', 'Loading user data...');
      expect(status).toHaveAttribute('aria-live', 'polite');
    });
  });

  // ========================================================================
  // SKELETON TESTS
  // ========================================================================

  describe('Skeleton', () => {
    it('should render skeleton element', () => {
      const { container } = render(<Skeleton />);
      const skeleton = container.querySelector('[aria-hidden="true"]');
      expect(skeleton).toBeInTheDocument();
    });

    it('should have animate-pulse by default', () => {
      const { container } = render(<Skeleton />);
      const skeleton = container.querySelector('[aria-hidden="true"]');
      expect(skeleton).toHaveClass('animate-pulse');
    });

    it('should not animate when animated is false', () => {
      const { container } = render(<Skeleton animated={false} />);
      const skeleton = container.querySelector('[aria-hidden="true"]');
      expect(skeleton).not.toHaveClass('animate-pulse');
    });

    it('should apply custom className', () => {
      const { container } = render(<Skeleton className="w-32 h-6" />);
      const skeleton = container.querySelector('[aria-hidden="true"]');
      expect(skeleton).toHaveClass('w-32', 'h-6');
    });

    it('should accept HTML attributes', () => {
      const { container } = render(<Skeleton data-testid="skeleton" />);
      expect(container.querySelector('[data-testid="skeleton"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // TEXT LINE SKELETON TESTS
  // ========================================================================

  describe('TextLineSkeleton', () => {
    it('should render a single line skeleton', () => {
      const { container } = render(<TextLineSkeleton />);
      const skeleton = container.querySelector('[aria-hidden="true"]');
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveClass('h-4', 'w-full');
    });

    it('should have status role for accessibility', () => {
      const { container } = render(<TextLineSkeleton />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // PARAGRAPH SKELETON TESTS
  // ========================================================================

  describe('ParagraphSkeleton', () => {
    it('should render default number of lines', () => {
      const { container } = render(<ParagraphSkeleton />);
      const lines = container.querySelectorAll('[aria-hidden="true"]');
      expect(lines).toHaveLength(3);
    });

    it('should render custom number of lines', () => {
      const { container } = render(<ParagraphSkeleton lines={5} />);
      const lines = container.querySelectorAll('[aria-hidden="true"]');
      expect(lines).toHaveLength(5);
    });

    it('should apply different width to last line', () => {
      const { container } = render(
        <ParagraphSkeleton lines={3} lastLineWidth="1/2" />
      );
      const lines = container.querySelectorAll('[aria-hidden="true"]');
      const lastLine = lines[2];
      expect(lastLine).toHaveClass('w-1/2');
    });

    it('should render all lines with full width except last', () => {
      const { container } = render(<ParagraphSkeleton lines={3} />);
      const lines = container.querySelectorAll('[aria-hidden="true"]');
      expect(lines[0]).toHaveClass('w-full');
      expect(lines[1]).toHaveClass('w-full');
      expect(lines[2]).toHaveClass('w-2/3');
    });

    it('should have status role for accessibility', () => {
      const { container } = render(<ParagraphSkeleton />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // CARD SKELETON TESTS
  // ========================================================================

  describe('CardSkeleton', () => {
    it('should render basic card skeleton', () => {
      const { container } = render(<CardSkeleton />);
      const card = container.querySelector('[role="status"]');
      expect(card).toHaveClass('rounded-lg', 'border', 'p-4');
    });

    it('should render card with image placeholder', () => {
      const { container } = render(<CardSkeleton hasImage />);
      const skeletons = container.querySelectorAll('[aria-hidden="true"]');
      expect(skeletons.length).toBeGreaterThan(1);
    });

    it('should render card with header skeleton', () => {
      const { container } = render(<CardSkeleton hasHeader />);
      const skeletons = container.querySelectorAll('[aria-hidden="true"]');
      expect(skeletons.length).toBeGreaterThan(1);
    });

    it('should render card with both image and header', () => {
      const { container } = render(<CardSkeleton hasImage hasHeader />);
      const skeletons = container.querySelectorAll('[aria-hidden="true"]');
      expect(skeletons.length).toBeGreaterThanOrEqual(4);
    });
  });

  // ========================================================================
  // TABLE SKELETON TESTS
  // ========================================================================

  describe('TableSkeleton', () => {
    it('should render table with default rows and columns', () => {
      const { container } = render(<TableSkeleton />);
      const rows = container.querySelectorAll('[aria-hidden="true"]');
      // 5 rows * 4 columns + 1 header * 4 columns = 24 skeletons
      expect(rows.length).toBe(24);
    });

    it('should render table with custom rows', () => {
      const { container } = render(<TableSkeleton rows={3} columns={2} />);
      const rows = container.querySelectorAll('[aria-hidden="true"]');
      // 3 rows * 2 columns + 1 header * 2 columns = 8 skeletons
      expect(rows.length).toBe(8);
    });

    it('should have proper table structure', () => {
      const { container } = render(<TableSkeleton rows={2} columns={2} />);
      const divs = container.querySelectorAll('.flex');
      // 1 header + 2 rows = 3 flex containers
      expect(divs.length).toBe(3);
    });

    it('should have status role for accessibility', () => {
      const { container } = render(<TableSkeleton />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // LIST SKELETON TESTS
  // ========================================================================

  describe('ListSkeleton', () => {
    it('should render default number of items', () => {
      const { container } = render(<ListSkeleton />);
      const items = container.querySelectorAll('.flex.gap-3');
      expect(items).toHaveLength(4);
    });

    it('should render custom number of items', () => {
      const { container } = render(<ListSkeleton count={6} />);
      const items = container.querySelectorAll('.flex.gap-3');
      expect(items).toHaveLength(6);
    });

    it('should render list with avatars', () => {
      const { container } = render(<ListSkeleton hasAvatar count={2} />);
      const avatars = container.querySelectorAll('.w-10.h-10');
      expect(avatars).toHaveLength(2);
    });

    it('should not render avatars when hasAvatar is false', () => {
      const { container } = render(<ListSkeleton hasAvatar={false} count={2} />);
      const avatars = container.querySelectorAll('.w-10.h-10.rounded-full');
      expect(avatars).toHaveLength(0);
    });

    it('should have status role for accessibility', () => {
      const { container } = render(<ListSkeleton />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // FORM SKELETON TESTS
  // ========================================================================

  describe('FormSkeleton', () => {
    it('should render default number of form fields', () => {
      const { container } = render(<FormSkeleton />);
      const fields = container.querySelectorAll('.space-y-4 > div');
      expect(fields).toHaveLength(3);
    });

    it('should render custom number of form fields', () => {
      const { container } = render(<FormSkeleton fields={5} />);
      const fields = container.querySelectorAll('.space-y-4 > div');
      expect(fields).toHaveLength(5);
    });

    it('should have label and input placeholders', () => {
      const { container } = render(<FormSkeleton fields={1} />);
      const skeletons = container.querySelectorAll('[aria-hidden="true"]');
      expect(skeletons.length).toBe(2); // label + input
    });

    it('should have status role for accessibility', () => {
      const { container } = render(<FormSkeleton />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // GRID SKELETON TESTS
  // ========================================================================

  describe('GridSkeleton', () => {
    it('should render default number of grid items', () => {
      const { container } = render(<GridSkeleton />);
      const items = container.querySelectorAll('.space-y-2');
      expect(items).toHaveLength(6);
    });

    it('should render custom number of grid items', () => {
      const { container } = render(<GridSkeleton count={12} />);
      const items = container.querySelectorAll('.space-y-2');
      expect(items).toHaveLength(12);
    });

    it('should have status role for accessibility', () => {
      const { container } = render(<GridSkeleton />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // PROGRESS BAR TESTS
  // ========================================================================

  describe('ProgressBar', () => {
    it('should render progress bar', () => {
      const { container } = render(<ProgressBar progress={50} />);
      expect(container.querySelector('[role="progressbar"]')).toBeInTheDocument();
    });

    it('should have correct aria attributes', () => {
      const { container } = render(<ProgressBar progress={75} />);
      const progressbar = container.querySelector('[role="progressbar"]');
      expect(progressbar).toHaveAttribute('aria-valuenow', '75');
      expect(progressbar).toHaveAttribute('aria-valuemin', '0');
      expect(progressbar).toHaveAttribute('aria-valuemax', '100');
    });

    it('should calculate percentage correctly', () => {
      const { container } = render(<ProgressBar progress={25} max={100} />);
      const progressbar = container.querySelector('[role="progressbar"]');
      expect(progressbar).toHaveAttribute('aria-valuenow', '25');
    });

    it('should clamp progress between 0 and 100', () => {
      const { rerender, container } = render(
        <ProgressBar progress={150} max={100} />
      );
      let progressbar = container.querySelector('[role="progressbar"]');
      expect(progressbar).toHaveAttribute('aria-valuenow', '100');

      rerender(<ProgressBar progress={-50} max={100} />);
      progressbar = container.querySelector('[role="progressbar"]');
      expect(progressbar).toHaveAttribute('aria-valuenow', '0');
    });

    it('should display percentage label when showLabel is true', () => {
      render(<ProgressBar progress={50} showLabel />);
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('should not display percentage label when showLabel is false', () => {
      const { container } = render(<ProgressBar progress={50} showLabel={false} />);
      expect(container.querySelector('p')).not.toBeInTheDocument();
    });

    it('should apply size classes', () => {
      const { container } = render(<ProgressBar progress={50} size="lg" />);
      const bar = container.querySelector('[role="progressbar"] > div');
      expect(bar).toHaveClass('h-3');
    });
  });

  // ========================================================================
  // LOADING OVERLAY TESTS
  // ========================================================================

  describe('LoadingOverlay', () => {
    it('should render children when not loading', () => {
      render(
        <LoadingOverlay isLoading={false}>
          <div>Content</div>
        </LoadingOverlay>
      );
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should show overlay when loading', () => {
      const { container } = render(
        <LoadingOverlay isLoading={true}>
          <div>Content</div>
        </LoadingOverlay>
      );
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });

    it('should display loading message', () => {
      render(
        <LoadingOverlay isLoading={true} message="Processing..." >
          <div>Content</div>
        </LoadingOverlay>
      );
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    it('should apply blur effect by default', () => {
      const { container } = render(
        <LoadingOverlay isLoading={true}>
          <div>Content</div>
        </LoadingOverlay>
      );
      const overlay = container.querySelector('[role="status"]');
      expect(overlay).toHaveClass('backdrop-blur-sm');
    });

    it('should not apply blur when blur is false', () => {
      const { container } = render(
        <LoadingOverlay isLoading={true} blur={false}>
          <div>Content</div>
        </LoadingOverlay>
      );
      const overlay = container.querySelector('[role="status"]')?.parentElement;
      expect(overlay).not.toHaveClass('backdrop-blur-sm');
    });

    it('should render both content and overlay together', () => {
      const { container } = render(
        <LoadingOverlay isLoading={true}>
          <div>Content</div>
        </LoadingOverlay>
      );
      expect(screen.getByText('Content')).toBeInTheDocument();
      const status = container.querySelector('[role="status"]');
      expect(status).toBeInTheDocument();
    });
  });

  // ========================================================================
  // SHIMMER SKELETON TESTS
  // ========================================================================

  describe('ShimmerSkeleton', () => {
    it('should render shimmer skeleton', () => {
      const { container } = render(<ShimmerSkeleton />);
      const shimmer = container.querySelector('[role="status"]');
      expect(shimmer).toBeInTheDocument();
    });

    it('should have shimmer animation style', () => {
      const { container } = render(<ShimmerSkeleton />);
      const shimmer = container.querySelector('[role="status"]');
      expect(shimmer).toHaveStyle({ animation: 'shimmer 2s infinite' });
    });

    it('should accept children', () => {
      render(
        <ShimmerSkeleton>
          <div>Shimmer Content</div>
        </ShimmerSkeleton>
      );
      // Note: children may not be visible due to styling, but should be in DOM
      const { container } = render(
        <ShimmerSkeleton>
          <span data-testid="shimmer-child">Content</span>
        </ShimmerSkeleton>
      );
      expect(container.querySelector('[data-testid="shimmer-child"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // PULSE SKELETON TESTS
  // ========================================================================

  describe('PulseSkeleton', () => {
    it('should render pulse skeleton', () => {
      const { container } = render(<PulseSkeleton />);
      expect(container.querySelector('[role="status"]')).toBeInTheDocument();
    });

    it('should have animate-pulse class', () => {
      const { container } = render(<PulseSkeleton />);
      const pulse = container.querySelector('[role="status"]');
      expect(pulse).toHaveClass('animate-pulse');
    });

    it('should accept children', () => {
      const { container } = render(
        <PulseSkeleton>
          <span data-testid="pulse-child">Content</span>
        </PulseSkeleton>
      );
      expect(container.querySelector('[data-testid="pulse-child"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // SKELETON WRAPPER TESTS
  // ========================================================================

  describe('SkeletonWrapper', () => {
    it('should render skeleton when isLoading is true', () => {
      const { container } = render(
        <SkeletonWrapper
          isLoading={true}
          skeleton={<div data-testid="skeleton">Skeleton</div>}
        >
          <div data-testid="content">Content</div>
        </SkeletonWrapper>
      );
      expect(container.querySelector('[data-testid="skeleton"]')).toBeInTheDocument();
      expect(container.querySelector('[data-testid="content"]')).not.toBeInTheDocument();
    });

    it('should render content when isLoading is false', () => {
      const { container } = render(
        <SkeletonWrapper
          isLoading={false}
          skeleton={<div data-testid="skeleton">Skeleton</div>}
        >
          <div data-testid="content">Content</div>
        </SkeletonWrapper>
      );
      expect(container.querySelector('[data-testid="content"]')).toBeInTheDocument();
      expect(container.querySelector('[data-testid="skeleton"]')).not.toBeInTheDocument();
    });

    it('should toggle between skeleton and content', () => {
      const { rerender, container } = render(
        <SkeletonWrapper
          isLoading={true}
          skeleton={<div data-testid="skeleton">Skeleton</div>}
        >
          <div data-testid="content">Content</div>
        </SkeletonWrapper>
      );

      expect(container.querySelector('[data-testid="skeleton"]')).toBeInTheDocument();

      rerender(
        <SkeletonWrapper
          isLoading={false}
          skeleton={<div data-testid="skeleton">Skeleton</div>}
        >
          <div data-testid="content">Content</div>
        </SkeletonWrapper>
      );

      expect(container.querySelector('[data-testid="content"]')).toBeInTheDocument();
    });
  });

  // ========================================================================
  // INTEGRATION TESTS
  // ========================================================================

  describe('Integration Tests', () => {
    it('should work together: LoadingState with SkeletonWrapper', () => {
      const { container, rerender } = render(
        <SkeletonWrapper
          isLoading={true}
          skeleton={
            <div data-testid="skeleton-loader">
              <CardSkeleton />
            </div>
          }
        >
          <div data-testid="card-content">Actual Card</div>
        </SkeletonWrapper>
      );

      expect(container.querySelector('[data-testid="skeleton-loader"]')).toBeInTheDocument();

      rerender(
        <SkeletonWrapper
          isLoading={false}
          skeleton={
            <div data-testid="skeleton-loader">
              <CardSkeleton />
            </div>
          }
        >
          <div data-testid="card-content">Actual Card</div>
        </SkeletonWrapper>
      );

      expect(container.querySelector('[data-testid="card-content"]')).toBeInTheDocument();
    });

    it('should combine ProgressBar with LoadingOverlay', () => {
      const { container } = render(
        <LoadingOverlay isLoading={true} message="Loading...">
          <ProgressBar progress={50} showLabel />
        </LoadingOverlay>
      );
      // Overlay should show even with progress bar
      const statusElements = container.querySelectorAll('[role="status"]');
      expect(statusElements.length).toBeGreaterThan(0);
    });

    it('should provide proper accessibility across components', () => {
      const { container } = render(
        <div>
          <LoadingState isLoading={true} ariaLabel="Loading data..." />
          <ParagraphSkeleton />
        </div>
      );

      const statuses = container.querySelectorAll('[role="status"]');
      expect(statuses.length).toBeGreaterThanOrEqual(2);

      // Check that LoadingState has aria-live
      const loadingStatus = Array.from(statuses).find(
        status => status.querySelector('svg')
      );
      expect(loadingStatus).toHaveAttribute('aria-live', 'polite');
    });
  });
});
