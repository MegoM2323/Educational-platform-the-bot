import React, { useState } from 'react';
import {
  Spinner,
  LoadingState,
  ProgressBar,
  CardSkeleton,
  TableSkeleton,
  ListSkeleton,
  FormSkeleton,
  GridSkeleton,
  LoadingOverlay,
  SkeletonWrapper,
  TextLineSkeleton,
  ParagraphSkeleton,
  ShimmerSkeleton,
  PulseSkeleton,
} from './Loading';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * LOADING COMPONENTS USAGE EXAMPLES
 *
 * This file demonstrates how to use all loading state and skeleton components
 * in various real-world scenarios.
 */

// ============================================================================
// EXAMPLE 1: Simple Spinner
// ============================================================================

export const SpinnerExample: React.FC = () => {
  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle>Spinner Sizes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Extra Small</p>
            <Spinner size="xs" />
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Small</p>
            <Spinner size="sm" />
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Medium (Default)</p>
            <Spinner size="md" />
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Large</p>
            <Spinner size="lg" />
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Extra Large</p>
            <Spinner size="xl" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// ============================================================================
// EXAMPLE 2: Loading with Progress
// ============================================================================

export const ProgressBarExample: React.FC = () => {
  const [progress, setProgress] = useState(0);

  const startSimulation = () => {
    setProgress(0);
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Progress Bar Example</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ProgressBar progress={progress} showLabel />
        <Button onClick={startSimulation}>Start Progress</Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 3: Skeleton Loaders - Text Content
// ============================================================================

export const TextSkeletonsExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Text Skeleton Examples</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <p className="text-sm text-muted-foreground mb-2">Single Line</p>
          {loading ? <TextLineSkeleton /> : <p>This is actual content</p>}
        </div>

        <div>
          <p className="text-sm text-muted-foreground mb-2">Paragraph (3 lines)</p>
          {loading ? (
            <ParagraphSkeleton lines={3} />
          ) : (
            <div className="space-y-2">
              <p>This is the first line of content.</p>
              <p>This is the second line.</p>
              <p>And this is the third line.</p>
            </div>
          )}
        </div>

        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 4: Card Loading
// ============================================================================

export const CardLoadingExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Card Skeleton</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <CardSkeleton hasImage hasHeader />
        ) : (
          <Card>
            <div className="h-40 bg-gradient-to-r from-primary to-primary/50" />
            <CardHeader>
              <CardTitle>Sample Card Title</CardTitle>
            </CardHeader>
            <CardContent>
              <p>This is the actual card content after loading.</p>
            </CardContent>
          </Card>
        )}
        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 5: Table Loading
// ============================================================================

export const TableLoadingExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Table Skeleton</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <TableSkeleton rows={5} columns={3} />
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Actual table content would appear here
            </p>
          </div>
        )}
        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 6: List Loading
// ============================================================================

export const ListLoadingExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>List Skeleton with Avatars</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <ListSkeleton count={3} hasAvatar />
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Actual list items would appear here
            </p>
          </div>
        )}
        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 7: Form Loading
// ============================================================================

export const FormLoadingExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Form Skeleton</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <FormSkeleton fields={4} />
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Actual form fields would appear here
            </p>
          </div>
        )}
        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 8: Grid/Gallery Loading
// ============================================================================

export const GridLoadingExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Grid Skeleton</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <GridSkeleton count={6} columns={3} aspectRatio="square" />
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Actual grid items would appear here
            </p>
          </div>
        )}
        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 9: Loading Overlay
// ============================================================================

export const LoadingOverlayExample: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    setLoading(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Loading Overlay Example</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <LoadingOverlay isLoading={loading} message="Processing...">
          <Card>
            <CardHeader>
              <CardTitle>Content</CardTitle>
            </CardHeader>
            <CardContent>
              <p>This content is overlaid with a loading state when processing.</p>
              <Button className="mt-4" onClick={handleSubmit}>
                Submit Form
              </Button>
            </CardContent>
          </Card>
        </LoadingOverlay>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 10: Skeleton Wrapper (Conditional Rendering)
// ============================================================================

export const SkeletonWrapperExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Skeleton Wrapper</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <SkeletonWrapper
          isLoading={loading}
          skeleton={<CardSkeleton hasImage hasHeader />}
        >
          <Card>
            <div className="h-40 bg-gradient-to-r from-blue-500 to-purple-500" />
            <CardHeader>
              <CardTitle>Actual Content</CardTitle>
            </CardHeader>
            <CardContent>
              <p>
                SkeletonWrapper automatically switches between skeleton and
                content based on the loading state.
              </p>
            </CardContent>
          </Card>
        </SkeletonWrapper>
        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 11: Shimmer Effect
// ============================================================================

export const ShimmerExample: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Shimmer Skeleton</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ShimmerSkeleton className="h-40 w-full rounded-lg" />
        <ShimmerSkeleton className="h-12 w-1/2 rounded-lg" />
        <ShimmerSkeleton className="h-4 w-full rounded-lg" />
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 12: Pulse Effect
// ============================================================================

export const PulseExample: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Pulse Skeleton</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <PulseSkeleton className="h-20 w-full rounded-lg" />
        <PulseSkeleton className="h-10 w-full rounded-lg" />
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 13: Complete Page Load Pattern
// ============================================================================

export const PageLoadPattern: React.FC = () => {
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    // Simulate data loading
    const timer = setTimeout(() => setLoading(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="space-y-6">
      <SkeletonWrapper
        isLoading={loading}
        skeleton={<TextLineSkeleton className="h-8 w-1/3" />}
      >
        <h1 className="text-3xl font-bold">Page Title</h1>
      </SkeletonWrapper>

      <SkeletonWrapper
        isLoading={loading}
        skeleton={<ParagraphSkeleton lines={3} />}
      >
        <p>
          This is the page content. It demonstrates how skeletons maintain the
          layout while content is loading.
        </p>
      </SkeletonWrapper>

      <SkeletonWrapper
        isLoading={loading}
        skeleton={<CardSkeleton />}
      >
        <Card>
          <CardHeader>
            <CardTitle>Content Card</CardTitle>
          </CardHeader>
          <CardContent>Content here</CardContent>
        </Card>
      </SkeletonWrapper>
    </div>
  );
};

// ============================================================================
// EXAMPLE 14: Data Fetch with Error Handling
// ============================================================================

export const DataFetchPattern: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      setData('Successfully loaded data');
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    loadData();
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Data Fetch Pattern</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading && <ProgressBar progress={50} />}
        {error && <p className="text-destructive">{error}</p>}
        {data && <p className="text-green-600">{data}</p>}
        <Button onClick={loadData}>Reload</Button>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// EXAMPLE 15: Responsive Skeletons
// ============================================================================

export const ResponsiveSkeletonsExample: React.FC = () => {
  const [loading, setLoading] = useState(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Responsive Grid Skeleton</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <p>Responsive content grid</p>
        )}
        <Button onClick={() => setLoading(!loading)}>
          {loading ? 'Show Content' : 'Show Loading'}
        </Button>
      </CardContent>
    </Card>
  );
};
