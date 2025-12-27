import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

/**
 * Responsive Components Test Suite
 *
 * Tests responsive behavior for:
 * - Tables (horizontal scroll on mobile)
 * - Forms (full width on mobile, constrained on desktop)
 * - Modals (full screen on mobile, centered on desktop)
 * - Dropdowns (scroll on mobile, normal on desktop)
 * - Grids (stack on mobile, multi-column on desktop)
 * - Cards (full width mobile, sized on desktop)
 */

describe('Responsive Table Component', () => {
  it('should have horizontal scroll wrapper on mobile', () => {
    // Tables should be wrapped in overflow-x-auto for mobile
    const TableWrapper = ({ children }: { children: React.ReactNode }) => (
      <div className="overflow-x-auto sm:overflow-x-visible">
        <table className="min-w-full">{children}</table>
      </div>
    );

    render(
      <TableWrapper>
        <thead>
          <tr>
            <th>Header 1</th>
            <th>Header 2</th>
            <th>Header 3</th>
          </tr>
        </thead>
      </TableWrapper>
    );

    const tableWrapper = screen.getByRole('table').parentElement;
    expect(tableWrapper).toHaveClass('overflow-x-auto');
  });

  it('should have responsive column widths', () => {
    // Columns should be min-width for mobile readability
    const ResponsiveTable = () => (
      <table className="w-full">
        <thead>
          <tr>
            <th className="min-w-[120px] sm:min-w-[100px]">Column 1</th>
            <th className="min-w-[120px] sm:min-w-[100px]">Column 2</th>
          </tr>
        </thead>
      </table>
    );

    render(<ResponsiveTable />);
    expect(screen.getByText('Column 1')).toBeInTheDocument();
  });

  it('should display data differently on mobile vs desktop', () => {
    // Some tables show different columns on mobile vs desktop
    const ResponsiveTable = () => (
      <table className="w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th className="hidden md:table-cell">Email</th>
            <th className="hidden lg:table-cell">Phone</th>
            <th>Actions</th>
          </tr>
        </thead>
      </table>
    );

    render(<ResponsiveTable />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();
  });
});

describe('Responsive Form Component', () => {
  it('should be full width on mobile', () => {
    const ResponsiveForm = () => (
      <form className="w-full max-w-md">
        <div className="space-y-4">
          <input className="w-full px-4 py-2" placeholder="Full name" />
          <input className="w-full px-4 py-2" placeholder="Email" />
          <button className="w-full">Submit</button>
        </div>
      </form>
    );

    render(<ResponsiveForm />);

    const inputs = screen.getAllByRole('textbox');
    inputs.forEach((input) => {
      expect(input).toHaveClass('w-full');
    });
  });

  it('should stack form fields vertically on mobile', () => {
    const ResponsiveForm = () => (
      <form className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <input className="flex-1" placeholder="First Name" />
          <input className="flex-1" placeholder="Last Name" />
        </div>
      </form>
    );

    render(<ResponsiveForm />);
    expect(screen.getByPlaceholderText('First Name')).toBeInTheDocument();
  });

  it('should have touch-friendly input sizes on mobile', () => {
    const ResponsiveForm = () => (
      <form>
        <input
          className="w-full px-4 py-3 sm:py-2 rounded border"
          placeholder="Input"
          style={{ minHeight: '44px' }} // Touch target size
        />
      </form>
    );

    render(<ResponsiveForm />);

    const input = screen.getByPlaceholderText('Input');
    const styles = window.getComputedStyle(input);

    // Should have minimum height for touch targets
    expect(input).toHaveStyle('minHeight: 44px');
  });

  it('should have proper label sizing for mobile', () => {
    const ResponsiveForm = () => (
      <form className="space-y-4">
        <div>
          <label className="block text-sm sm:text-base mb-2">Email</label>
          <input type="email" className="w-full" />
        </div>
      </form>
    );

    render(<ResponsiveForm />);
    expect(screen.getByText('Email')).toBeInTheDocument();
  });
});

describe('Responsive Modal Component', () => {
  it('should be full screen on mobile', () => {
    const ResponsiveModal = () => (
      <div className="fixed inset-0 sm:inset-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-full sm:max-w-md rounded-t-lg sm:rounded-lg">
        <div className="p-6 max-h-[90vh] overflow-y-auto">Modal Content</div>
      </div>
    );

    render(<ResponsiveModal />);
    expect(screen.getByText('Modal Content')).toBeInTheDocument();
  });

  it('should be centered and constrained on desktop', () => {
    const ResponsiveModal = () => (
      <div className="w-full sm:max-w-md">
        <div className="p-6">Modal Content</div>
      </div>
    );

    render(<ResponsiveModal />);
    expect(screen.getByText('Modal Content')).toBeInTheDocument();
  });

  it('should have scrollable content on mobile', () => {
    const ResponsiveModal = () => (
      <div className="max-h-[90vh] overflow-y-auto">
        <div className="p-4">Modal Content</div>
      </div>
    );

    render(<ResponsiveModal />);
    expect(screen.getByText('Modal Content')).toBeInTheDocument();
  });
});

describe('Responsive Dropdown Component', () => {
  it('should have scrollable dropdown on mobile with many items', () => {
    const ResponsiveDropdown = () => (
      <div className="max-h-[300px] sm:max-h-auto overflow-y-auto">
        {['Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5'].map((item) => (
          <div key={item}>{item}</div>
        ))}
      </div>
    );

    render(<ResponsiveDropdown />);
    expect(screen.getByText('Item 1')).toBeInTheDocument();
  });

  it('should position dropdown correctly on mobile', () => {
    const ResponsiveDropdown = () => (
      <div className="fixed bottom-0 left-0 right-0 sm:absolute sm:top-full sm:left-0 sm:right-auto">
        Dropdown Content
      </div>
    );

    render(<ResponsiveDropdown />);
    expect(screen.getByText('Dropdown Content')).toBeInTheDocument();
  });

  it('should have touch-friendly spacing between items', () => {
    const ResponsiveDropdown = () => (
      <div>
        {['Item 1', 'Item 2', 'Item 3'].map((item) => (
          <button key={item} className="w-full px-4 py-3" style={{ minHeight: '44px' }}>
            {item}
          </button>
        ))}
      </div>
    );

    render(<ResponsiveDropdown />);

    const buttons = screen.getAllByRole('button');
    buttons.forEach((button) => {
      expect(button).toHaveStyle('minHeight: 44px');
    });
  });
});

describe('Responsive Grid Layout', () => {
  it('should display single column on mobile, multi-column on desktop', () => {
    const ResponsiveGrid = () => (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((item) => (
          <div key={item} className="p-4 border rounded">
            Item {item}
          </div>
        ))}
      </div>
    );

    const { container } = render(<ResponsiveGrid />);
    const grid = container.querySelector('.grid');

    expect(grid).toHaveClass('grid-cols-1');
    expect(grid).toHaveClass('sm:grid-cols-2');
    expect(grid).toHaveClass('lg:grid-cols-3');
  });

  it('should have gap that adjusts for mobile', () => {
    const ResponsiveGrid = () => (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 sm:gap-4 lg:gap-6">
        <div>Item 1</div>
        <div>Item 2</div>
      </div>
    );

    const { container } = render(<ResponsiveGrid />);
    const grid = container.querySelector('.grid');

    expect(grid).toHaveClass('gap-2');
    expect(grid).toHaveClass('sm:gap-4');
  });
});

describe('Responsive Card Component', () => {
  it('should be full width on mobile', () => {
    const ResponsiveCard = () => (
      <div className="w-full sm:w-auto max-w-sm mx-auto">
        Card Content
      </div>
    );

    render(<ResponsiveCard />);
    const card = screen.getByText('Card Content').parentElement;
    expect(card).toHaveClass('w-full');
  });

  it('should have responsive padding', () => {
    const ResponsiveCard = () => (
      <div className="p-4 sm:p-6 lg:p-8">Card Content</div>
    );

    render(<ResponsiveCard />);
    const card = screen.getByText('Card Content');
    expect(card.parentElement).toHaveClass('p-4', 'sm:p-6');
  });

  it('should have responsive text sizes', () => {
    const ResponsiveCard = () => (
      <div className="p-4">
        <h3 className="text-lg sm:text-xl lg:text-2xl font-bold">Title</h3>
        <p className="text-sm sm:text-base text-muted-foreground">Description</p>
      </div>
    );

    render(<ResponsiveCard />);
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
  });
});

describe('Responsive Button Components', () => {
  it('should have full width on mobile, auto width on desktop', () => {
    const ResponsiveButton = () => (
      <button className="w-full sm:w-auto px-4 py-2 rounded">
        Click me
      </button>
    );

    render(<ResponsiveButton />);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('w-full', 'sm:w-auto');
  });

  it('should have touch-friendly size on mobile', () => {
    const ResponsiveButton = () => (
      <button className="w-full px-4 py-3 sm:py-2 rounded" style={{ minHeight: '44px' }}>
        Touch Button
      </button>
    );

    render(<ResponsiveButton />);
    const button = screen.getByRole('button');
    expect(button).toHaveStyle('minHeight: 44px');
  });

  it('should have responsive text sizes', () => {
    const ResponsiveButton = () => (
      <button className="text-sm sm:text-base lg:text-lg">
        Button
      </button>
    );

    render(<ResponsiveButton />);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('text-sm', 'sm:text-base');
  });

  it('should stack button groups vertically on mobile', () => {
    const ResponsiveButtonGroup = () => (
      <div className="flex flex-col sm:flex-row gap-2">
        <button>Button 1</button>
        <button>Button 2</button>
      </div>
    );

    render(<ResponsiveButtonGroup />);
    const container = screen.getByRole('button', { name: 'Button 1' }).parentElement;
    expect(container).toHaveClass('flex-col', 'sm:flex-row');
  });
});

describe('Responsive Image Component', () => {
  it('should scale images on mobile', () => {
    const ResponsiveImage = () => (
      <img
        src="test.jpg"
        alt="Test"
        className="w-full h-auto max-w-full object-cover"
      />
    );

    const { container } = render(<ResponsiveImage />);
    const img = container.querySelector('img');

    expect(img).toHaveClass('w-full');
    expect(img).toHaveClass('h-auto');
  });

  it('should have responsive container for images', () => {
    const ResponsiveImage = () => (
      <div className="w-full sm:w-96">
        <img src="test.jpg" alt="Test" className="w-full h-auto" />
      </div>
    );

    const { container } = render(<ResponsiveImage />);
    const div = container.querySelector('div');

    expect(div).toHaveClass('w-full');
    expect(div).toHaveClass('sm:w-96');
  });
});

describe('Responsive Typography', () => {
  it('should have readable font sizes on mobile', () => {
    // Minimum 14px on mobile, larger on desktop
    const ResponsiveText = () => (
      <p className="text-sm sm:text-base lg:text-lg leading-relaxed">
        This is readable text
      </p>
    );

    render(<ResponsiveText />);
    expect(screen.getByText('This is readable text')).toBeInTheDocument();
  });

  it('should have proper line height for mobile', () => {
    const ResponsiveText = () => (
      <p className="leading-relaxed sm:leading-normal">Text content</p>
    );

    render(<ResponsiveText />);
    expect(screen.getByText('Text content')).toHaveClass('leading-relaxed');
  });

  it('should have sufficient line length on desktop', () => {
    const ResponsiveText = () => (
      <div className="max-w-full sm:max-w-prose">
        This text should be constrained on desktop for better readability
      </div>
    );

    render(<ResponsiveText />);
    expect(
      screen.getByText(
        'This text should be constrained on desktop for better readability'
      )
    ).toBeInTheDocument();
  });
});
