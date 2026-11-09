import SuperAdminShell from "@/components/superadmin/SuperAdminShell";

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  return <SuperAdminShell>{children}</SuperAdminShell>;
}
