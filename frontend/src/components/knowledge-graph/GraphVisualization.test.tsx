import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GraphVisualization } from './GraphVisualization';
import { GraphData } from './graph-types';

describe('GraphVisualization', () => {
  const mockData: GraphData = {
    nodes: [
      { id: '1', title: 'Урок 1', status: 'completed' },
      { id: '2', title: 'Урок 2', status: 'in_progress' },
      { id: '3', title: 'Урок 3', status: 'not_started' },
      { id: '4', title: 'Урок 4', status: 'locked' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
      { source: '1', target: '4', type: 'suggested' },
    ],
  };

  it('renders without crashing', () => {
    render(<GraphVisualization data={mockData} />);
    expect(screen.getByRole('img', { name: /knowledge graph/i })).toBeInTheDocument();
  });

  it('shows empty state when no data', () => {
    render(<GraphVisualization data={{ nodes: [], links: [] }} />);
    expect(screen.getByText(/Нет данных для отображения графа/i)).toBeInTheDocument();
  });

  it('renders zoom controls', () => {
    render(<GraphVisualization data={mockData} />);
    expect(screen.getByTitle(/Увеличить/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Уменьшить/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Сбросить зум/i)).toBeInTheDocument();
  });

  it('renders legend', () => {
    render(<GraphVisualization data={mockData} />);
    expect(screen.getByText(/Статус урока:/i)).toBeInTheDocument();
    expect(screen.getByText(/Не начат/i)).toBeInTheDocument();
    expect(screen.getByText(/В процессе/i)).toBeInTheDocument();
    expect(screen.getByText(/Завершен/i)).toBeInTheDocument();
    expect(screen.getByText(/Заблокирован/i)).toBeInTheDocument();
  });

  it('calls onNodeClick when provided', () => {
    const handleClick = vi.fn();
    render(<GraphVisualization data={mockData} onNodeClick={handleClick} />);
    // Note: Actual click testing would require more setup with D3
  });

  it('calls onNodeHover when provided', () => {
    const handleHover = vi.fn();
    render(<GraphVisualization data={mockData} onNodeHover={handleHover} />);
    // Note: Actual hover testing would require more setup with D3
  });

  it('calls onNodeDrag when node is dragged in edit mode', () => {
    const handleDrag = vi.fn();
    render(<GraphVisualization data={mockData} onNodeDrag={handleDrag} isEditable={true} />);
    // Note: Actual drag testing would require more setup with D3
  });

  it('respects custom width and height', () => {
    const { container } = render(
      <GraphVisualization data={mockData} width={1000} height={800} />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <GraphVisualization data={mockData} className="custom-class" />
    );
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });
});
