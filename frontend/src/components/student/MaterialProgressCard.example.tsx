/**
 * MaterialProgressCard Examples
 * Demonstrates usage of the enhanced material progress component
 */

import { MaterialProgressCard } from "./MaterialProgressCard";
import { CircularProgressIndicator } from "./CircularProgressIndicator";
import { ProgressHistoryChart } from "./ProgressHistoryChart";

export function MaterialProgressCardExample() {
  const mockHistoryData = [
    {
      timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      progress: 20,
      timeSpent: 120,
      note: "Started chapter 1",
    },
    {
      timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      progress: 40,
      timeSpent: 300,
      note: "Completed chapter 1 exercises",
    },
    {
      timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      progress: 65,
      timeSpent: 420,
      note: "Finished chapter 2",
    },
    {
      timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      progress: 85,
      timeSpent: 540,
      note: "Chapter 3 review",
    },
    {
      timestamp: new Date().toISOString(),
      progress: 95,
      timeSpent: 600,
      note: "Final assessments",
    },
  ];

  return (
    <div className="space-y-8 p-8">
      {/* Example 1: In Progress Material */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">In Progress Material</h2>
        <MaterialProgressCard
          material={{
            id: 1,
            title: "Algebra Basics",
            description: "Learn fundamental algebraic concepts and equations",
          }}
          progress={65}
          status="in_progress"
          timeSpent={180}
          lastAccessed={new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()}
          score={78}
          maxScore={100}
          nextMilestone={75}
          historyData={mockHistoryData}
          enableOfflineSync={true}
          showCompletionAnimation={true}
        />
      </section>

      {/* Example 2: Completed Material */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Completed Material</h2>
        <MaterialProgressCard
          material={{
            id: 2,
            title: "Geometry Fundamentals",
            description: "Master shapes, angles, and spatial relationships",
          }}
          progress={100}
          status="completed"
          timeSpent={720}
          lastAccessed={new Date().toISOString()}
          score={95}
          maxScore={100}
          nextMilestone={undefined}
          historyData={mockHistoryData}
          enableOfflineSync={true}
          showCompletionAnimation={true}
        />
      </section>

      {/* Example 3: Not Started Material */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Not Started Material</h2>
        <MaterialProgressCard
          material={{
            id: 3,
            title: "Trigonometry",
            description: "Explore trigonometric functions and identities",
          }}
          progress={0}
          status="not_started"
          timeSpent={0}
          historyData={[]}
          enableOfflineSync={true}
        />
      </section>

      {/* Example 4: Circular Progress Indicators */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Circular Progress Indicators</h2>
        <div className="grid gap-8 md:grid-cols-3">
          <div>
            <h3 className="mb-4 font-semibold">Not Started</h3>
            <CircularProgressIndicator
              progress={0}
              status="not_started"
              size={140}
              showLabel={true}
            />
          </div>

          <div>
            <h3 className="mb-4 font-semibold">In Progress (65%)</h3>
            <CircularProgressIndicator
              progress={65}
              status="in_progress"
              size={140}
              showLabel={true}
            />
          </div>

          <div>
            <h3 className="mb-4 font-semibold">Completed</h3>
            <CircularProgressIndicator
              progress={100}
              status="completed"
              size={140}
              showLabel={true}
            />
          </div>
        </div>
      </section>

      {/* Example 5: Progress History Chart */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Progress History</h2>
        <ProgressHistoryChart
          data={mockHistoryData}
          height={300}
          showTooltip={true}
          showGrid={true}
        />
      </section>

      {/* Example 6: Multiple Progress States */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Different Progress Levels</h2>
        <div className="grid gap-4 md:grid-cols-5">
          {[0, 25, 50, 75, 100].map((progress) => (
            <div key={progress} className="flex flex-col items-center gap-2">
              <CircularProgressIndicator
                progress={progress}
                status={
                  progress === 0
                    ? "not_started"
                    : progress === 100
                      ? "completed"
                      : "in_progress"
                }
                size={100}
                showLabel={true}
              />
            </div>
          ))}
        </div>
      </section>

      {/* Example 7: Loading State */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Loading State</h2>
        <MaterialProgressCard
          material={{
            id: 4,
            title: "Loading Example",
            description: "Shows loading skeleton",
          }}
          progress={0}
          status="not_started"
          isLoading={true}
        />
      </section>

      {/* Example 8: Error State */}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Error State</h2>
        <MaterialProgressCard
          material={{
            id: 5,
            title: "Error Example",
            description: "Shows error message with retry button",
          }}
          progress={0}
          status="not_started"
          error="Failed to load progress data"
          onRetry={() => alert("Retry clicked!")}
        />
      </section>
    </div>
  );
}

/**
 * Stories for Storybook or component documentation
 */
export const stories = {
  inProgress: {
    material: {
      id: 1,
      title: "Algebra Basics",
      description: "Learn fundamental algebraic concepts",
    },
    progress: 65,
    status: "in_progress",
    timeSpent: 180,
  },
  completed: {
    material: {
      id: 2,
      title: "Geometry Fundamentals",
      description: "Master shapes and angles",
    },
    progress: 100,
    status: "completed",
    timeSpent: 720,
  },
  notStarted: {
    material: {
      id: 3,
      title: "Trigonometry",
      description: "Explore trigonometric functions",
    },
    progress: 0,
    status: "not_started",
    timeSpent: 0,
  },
};
