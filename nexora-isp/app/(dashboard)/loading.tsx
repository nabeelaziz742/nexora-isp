import PageLoader from "@/components/ui/PageLoader";

export default function DashboardLoading() {
  return (
    <div className="flex h-full min-h-[450px] w-full items-center justify-center p-8">
      <PageLoader
        message="Loading workspace module..."
        subtext="Synchronizing real-time telemetry and operational state"
        fullscreen={false}
      />
    </div>
  );
}
