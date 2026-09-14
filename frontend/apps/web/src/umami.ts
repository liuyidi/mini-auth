const UMAMI_APP = "auth";

declare global {
  interface Window {
    umami?: {
      track: (event: string, data?: Record<string, unknown>) => void;
    };
  }
}

export function trackUmami(
  event: string,
  data: Record<string, string | number | boolean | undefined | null> = {},
): void {
  if (typeof window === "undefined") return;
  const payload: Record<string, string | number | boolean> = { app: UMAMI_APP };
  for (const [key, value] of Object.entries(data)) {
    if (value === undefined || value === null || value === "") continue;
    payload[key] = value;
  }
  try {
    window.umami?.track?.(event, payload);
  } catch {
    /* ignore */
  }
}
