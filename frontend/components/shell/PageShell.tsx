import SiteNav from '@/components/ui/SiteNav';

/** Shared chrome for the secondary routes: same charcoal theme, nav and gutters as Home/Bots. */
export default function PageShell({
  eyebrow,
  title,
  subtitle,
  aside,
  children,
}: {
  eyebrow: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  aside?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <main className="relative min-h-screen w-full overflow-x-hidden pb-24">
      <SiteNav />
      <div className="pt-[150px]" style={{ paddingLeft: 'var(--hub-gutter)', paddingRight: 'var(--hub-gutter)' }}>
        <div className="flex flex-col gap-8 min-[1024px]:flex-row min-[1024px]:items-end min-[1024px]:justify-between">
          <div>
            <p className="text-[16px] font-bold uppercase leading-none tracking-[0.16em] text-[#D8D8DE]">{eyebrow}</p>
            <h1 className="mt-[22px] text-[clamp(3.1rem,4.7vw,4.5rem)] font-extrabold leading-[0.96] tracking-[-0.045em] text-white">
              {title}
            </h1>
            {subtitle && <p className="mt-[20px] max-w-[46ch] text-[18.5px] leading-snug tracking-[-0.01em] text-[#B8B8C2]">{subtitle}</p>}
          </div>
          {aside}
        </div>
        <div className="mt-[44px] border-t border-white/[0.15] pt-[32px]">{children}</div>
      </div>
    </main>
  );
}
