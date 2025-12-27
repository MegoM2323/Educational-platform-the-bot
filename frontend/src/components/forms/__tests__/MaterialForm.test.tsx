import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MaterialForm } from "../MaterialForm";

// Mock the API client
vi.mock("@/integrations/api/unifiedClient", () => ({
  unifiedAPI: {
    request: vi.fn(() => Promise.resolve({ data: [] }))
  }
}));

// Mock the toast hook
vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn()
  })
}));

// Mock the logger
vi.mock("@/utils/logger", () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn()
  }
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe("MaterialForm Component", () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form with all required fields", async () => {
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByText(/создание материала/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/Название материала/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Краткое описание/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Содержание материала/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Предмет/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Тип материала/)).toBeInTheDocument();
  });

  it("displays character counter for title field", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const titleInput = screen.getByLabelText(/название материала/i);

    // Type some text
    await user.type(titleInput, "Test Material");

    // Check character counter appears
    expect(screen.getByText(/13\/200/)).toBeInTheDocument();
  });

  it("displays character counter for description field", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const descriptionInput = screen.getByLabelText(/краткое описание/i);

    await user.type(descriptionInput, "Test description");

    // Check character counter
    expect(screen.getByText(/16\/5000/)).toBeInTheDocument();
  });

  it("displays character counter for content field", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const contentInput = screen.getByLabelText(/содержание материала/i);

    await user.type(contentInput, "Test content material");

    // Look for content character counter
    const counters = screen.getAllByText(/\/50000/);
    expect(counters.length).toBeGreaterThan(0);
  });

  it("validates title is required", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const submitButton = screen.getByRole("button", {
      name: /создать материал/i
    });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/название материала обязательно/i)).toBeInTheDocument();
    });
  });

  it("validates title max length (200 chars)", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const titleInput = screen.getByLabelText(/название материала/i);

    // Type more than 200 characters
    const longTitle = "a".repeat(201);
    await user.type(titleInput, longTitle);

    const submitButton = screen.getByRole("button", {
      name: /создать материал/i
    });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/название не может быть длиннее 200 символов/i)).toBeInTheDocument();
    });
  });

  it("validates content is required", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const titleInput = screen.getByLabelText(/название материала/i);
    await user.type(titleInput, "Test Title");

    const submitButton = screen.getByRole("button", {
      name: /создать материал/i
    });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/содержание материала обязательно/i)).toBeInTheDocument();
    });
  });

  it("validates content max length (50000 chars)", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const contentInput = screen.getByLabelText(/содержание материала/i);

    // Type more than 50000 characters
    const longContent = "a".repeat(50001);
    await user.type(contentInput, longContent);

    const submitButton = screen.getByRole("button", {
      name: /создать материал/i
    });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/содержание не может быть длиннее 50000 символов/i)).toBeInTheDocument();
    });
  });

  it("validates description max length (5000 chars)", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const descriptionInput = screen.getByLabelText(/краткое описание/i);

    // Type more than 5000 characters
    const longDescription = "a".repeat(5001);
    await user.type(descriptionInput, longDescription);

    const submitButton = screen.getByRole("button", {
      name: /создать материал/i
    });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/описание не может быть длиннее 5000 символов/i)).toBeInTheDocument();
    });
  });

  it("validates file size", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const fileInput = screen.getByLabelText(/прикрепить файл материала/i);

    // Create a file larger than 10MB
    const largeFile = new File(
      ["x".repeat(11 * 1024 * 1024)],
      "large.pdf",
      { type: "application/pdf" }
    );

    await user.upload(fileInput, largeFile);

    await waitFor(() => {
      expect(screen.getByText(/размер файла не должен превышать/i)).toBeInTheDocument();
    });
  });

  it("validates file type", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const fileInput = screen.getByLabelText(/прикрепить файл материала/i);

    // Create a file with unsupported type
    const invalidFile = new File(
      ["content"],
      "file.exe",
      { type: "application/x-msdownload" }
    );

    await user.upload(fileInput, invalidFile);

    await waitFor(() => {
      expect(screen.getByText(/неподдерживаемый тип файла/i)).toBeInTheDocument();
    });
  });

  it("displays file preview with size", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const fileInput = screen.getByLabelText(/прикрепить файл материала/i);

    const validFile = new File(
      ["content"],
      "test.pdf",
      { type: "application/pdf" }
    );

    await user.upload(fileInput, validFile);

    await waitFor(() => {
      expect(screen.getByText(/test\.pdf/)).toBeInTheDocument();
    });
  });

  it("allows removing selected file", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const fileInput = screen.getByLabelText(/прикрепить файл материала/i);

    const validFile = new File(
      ["content"],
      "test.pdf",
      { type: "application/pdf" }
    );

    await user.upload(fileInput, validFile);

    // Wait for file preview to appear
    await waitFor(() => {
      expect(screen.getByText(/test\.pdf/)).toBeInTheDocument();
    });

    // Find and click the remove button (has Trash2 icon)
    const removeButton = screen.getByRole("button", { name: "" });
    await user.click(removeButton);

    // File preview should be gone
    await waitFor(() => {
      expect(screen.queryByText(/test\.pdf/)).not.toBeInTheDocument();
    });
  });

  it("validates subject is required", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const titleInput = screen.getByLabelText(/название материала/i);
    const contentInput = screen.getByLabelText(/содержание материала/i);

    await user.type(titleInput, "Test Title");
    await user.type(contentInput, "Test Content");

    const submitButton = screen.getByRole("button", {
      name: /создать материал/i
    });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/выберите предмет/i)).toBeInTheDocument();
    });
  });

  it("validates video URL format", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const videoUrlInput = screen.getByLabelText(/ссылка на видео/i);

    await user.type(videoUrlInput, "not-a-valid-url");

    const submitButton = screen.getByRole("button", {
      name: /создать материал/i
    });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/некорректный url видео/i)).toBeInTheDocument();
    });
  });

  it("calls onCancel when cancel button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const cancelButton = screen.getByRole("button", { name: /отмена/i });

    await user.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledOnce();
  });

  it("displays content field toggle button", () => {
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/показать/i)).toBeInTheDocument();
  });

  it("toggles content field visibility", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const toggleButton = screen.getByText(/показать/i);

    // Click to show
    await user.click(toggleButton);
    expect(screen.getByText(/скрыть/i)).toBeInTheDocument();

    // Click to hide
    await user.click(toggleButton);
    expect(screen.getByText(/показать/i)).toBeInTheDocument();
  });

  it("displays public checkbox with description", () => {
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/публичный материал/i)).toBeInTheDocument();
    expect(screen.getByText(/доступен всем студентам/i)).toBeInTheDocument();
  });

  it("pre-fills form with initial data", () => {
    const initialData = {
      title: "Existing Material",
      description: "Material Description",
      content: "Material Content",
      subject: "1",
      type: "lesson" as const,
      status: "active" as const,
      tags: "math, algebra",
      video_url: "https://youtube.com/watch?v=test"
    };

    render(
      <MaterialForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        initialData={initialData}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByDisplayValue(/existing material/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/material description/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/material content/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/math, algebra/i)).toBeInTheDocument();
  });

  it("shows edit title when isEditing prop is true", () => {
    render(
      <MaterialForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isEditing={true}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/редактирование материала/i)).toBeInTheDocument();
  });

  it("disables submit button when isLoading is true", () => {
    render(
      <MaterialForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isLoading={true}
      />,
      { wrapper: createWrapper() }
    );

    const submitButton = screen.getByRole("button", {
      name: /создание/i
    });

    expect(submitButton).toBeDisabled();
  });

  it("displays valid file type in preview", async () => {
    const user = userEvent.setup();
    render(
      <MaterialForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />,
      { wrapper: createWrapper() }
    );

    const fileInput = screen.getByLabelText(/прикрепить файл материала/i);

    const validFile = new File(
      ["content"],
      "document.docx",
      { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }
    );

    await user.upload(fileInput, validFile);

    await waitFor(() => {
      expect(screen.getByText(/document\.docx/)).toBeInTheDocument();
    });
  });
});
