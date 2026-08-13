import type {
  NotificationChannelSetting,
  NotificationEventSetting,
} from "@/types/settings";

interface NotificationSettingsProps {
  channels: NotificationChannelSetting[];
  events: NotificationEventSetting[];
}

export default function NotificationSettings({
  channels,
  events,
}: NotificationSettingsProps) {
  return (
    <div className="space-y-6">
      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">
            Notification Channels
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Customer communication delivery channels
          </p>
        </div>

        <div className="grid gap-px bg-[#202938] md:grid-cols-2">
          {channels.map((channel) => (
            <div
              key={channel.id}
              className="bg-[#0D1117] p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-200">
                    {channel.name}
                  </p>

                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    {channel.description}
                  </p>
                </div>

                <div
                  className={`relative mt-1 h-5 w-9 shrink-0 ${
                    channel.enabled
                      ? "bg-blue-600"
                      : "bg-slate-700"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 h-4 w-4 bg-white ${
                      channel.enabled
                        ? "left-[18px]"
                        : "left-0.5"
                    }`}
                  />
                </div>
              </div>

              <div className="mt-4 border-t border-[#202938] pt-3">
                <span
                  className={`text-[10px] font-medium ${
                    channel.enabled
                      ? "text-amber-400"
                      : "text-slate-600"
                  }`}
                >
                  {channel.statusLabel}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="overflow-hidden border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">
            Notification Event Matrix
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Channel routing by operational customer event
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] border-collapse">
            <thead>
              <tr className="border-b border-[#202938] bg-[#0A0E14]">
                <TableHead>Operational Event</TableHead>
                <TableHead>WhatsApp</TableHead>
                <TableHead>SMS</TableHead>
                <TableHead>Email</TableHead>
              </tr>
            </thead>

            <tbody>
              {events.map((event) => (
                <tr
                  key={event.id}
                  className="border-b border-[#202938] last:border-b-0"
                >
                  <td className="px-5 py-4">
                    <p className="text-xs font-medium text-slate-200">
                      {event.eventName}
                    </p>

                    <p className="mt-1 max-w-2xl text-[11px] leading-5 text-slate-500">
                      {event.description}
                    </p>
                  </td>

                  <ChannelCell enabled={event.whatsapp} />
                  <ChannelCell enabled={event.sms} />
                  <ChannelCell enabled={event.email} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

interface TableHeadProps {
  children: React.ReactNode;
}

function TableHead({ children }: TableHeadProps) {
  return (
    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
      {children}
    </th>
  );
}

interface ChannelCellProps {
  enabled: boolean;
}

function ChannelCell({
  enabled,
}: ChannelCellProps) {
  return (
    <td className="px-5 py-4">
      <span
        className={`inline-flex px-2 py-1 text-[10px] font-semibold ${
          enabled
            ? "bg-emerald-500/10 text-emerald-400"
            : "bg-slate-500/10 text-slate-600"
        }`}
      >
        {enabled ? "ENABLED" : "OFF"}
      </span>
    </td>
  );
}