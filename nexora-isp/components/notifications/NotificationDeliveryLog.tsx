import type {
  NotificationDeliveryLogItem,
  NotificationDeliveryLogStatus,
} from "@/types/notifications";

interface NotificationDeliveryLogProps {
  deliveries: NotificationDeliveryLogItem[];
}

const statusStyles: Record<
  NotificationDeliveryLogStatus,
  string
> = {
  PENDING: "bg-amber-500/10 text-amber-400",
  PROCESSING: "bg-blue-500/10 text-blue-400",
  SENT: "bg-emerald-500/10 text-emerald-400",
  DELIVERED: "bg-emerald-500/10 text-emerald-400",
  FAILED: "bg-red-500/10 text-red-400",
  CANCELLED: "bg-slate-500/10 text-slate-400",
};

function formatEventType(eventType: string): string {
  return eventType
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

export default function NotificationDeliveryLog({
  deliveries,
}: NotificationDeliveryLogProps) {
  return (
    <section className="overflow-hidden border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-100">
          Notification Delivery Log
        </h2>

        <p className="mt-1 text-[11px] text-slate-500">
          Real tenant-scoped communication delivery audit
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1050px] border-collapse">
          <thead>
            <tr className="border-b border-[#202938] bg-[#0A0E14]">
              <TableHead>Customer</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Channel</TableHead>
              <TableHead>Message Context</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Triggered</TableHead>
            </tr>
          </thead>

          <tbody>
            {deliveries.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-12 text-center text-xs text-slate-500"
                >
                  No notification jobs found.
                </td>
              </tr>
            ) : (
              deliveries.map((delivery) => (
                <tr
                  key={delivery.id}
                  className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]/60"
                >
                  <TableCell>
                    <p className="text-xs font-medium text-slate-200">
                      {delivery.customerName}
                    </p>

                    <p className="mt-1 font-mono text-[10px] text-blue-400">
                      {delivery.customerCode}
                    </p>
                  </TableCell>

                  <TableCell>
                    <p className="text-[11px] text-slate-300">
                      {formatEventType(
                        delivery.eventType,
                      )}
                    </p>

                    <p className="mt-1 font-mono text-[9px] text-slate-600">
                      {delivery.eventCode}
                    </p>
                  </TableCell>

                  <TableCell>
                    <span className="border border-[#202938] bg-[#121821] px-2 py-1 text-[9px] font-semibold text-slate-400">
                      {delivery.channel}
                    </span>
                  </TableCell>

                  <TableCell>
                    <span className="line-clamp-2 max-w-md text-[11px] text-slate-500">
                      {delivery.messageContext}
                    </span>
                  </TableCell>

                  <TableCell>
                    <span
                      className={`inline-flex px-2 py-1 text-[9px] font-semibold ${
                        statusStyles[delivery.status]
                      }`}
                    >
                      {delivery.status}
                    </span>
                  </TableCell>

                  <TableCell>
                    <span className="text-[10px] text-slate-600">
                      {delivery.triggeredAt}
                    </span>
                  </TableCell>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

interface TableHeadProps {
  children: React.ReactNode;
}

function TableHead({
  children,
}: TableHeadProps) {
  return (
    <th className="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.08em] text-slate-500">
      {children}
    </th>
  );
}

interface TableCellProps {
  children: React.ReactNode;
}

function TableCell({
  children,
}: TableCellProps) {
  return (
    <td className="px-4 py-3 align-middle">
      {children}
    </td>
  );
}