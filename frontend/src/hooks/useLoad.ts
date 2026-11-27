import { useCallback, useEffect, useState } from "react";

export type LoadState<T> = { status: "loading" } | { status: "ok"; data: T } | { status: "error"; error: unknown };

/**
 * Runs `loader` on mount and whenever it changes (wrap it in useCallback) or
 * `reload()` is called. Keeps the previous data visible while reloading.
 */
export function useLoad<T>(loader: () => Promise<T>): { state: LoadState<T>; reload: () => void } {
  const [state, setState] = useState<LoadState<T>>({ status: "loading" });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    loader().then(
      (data) => {
        if (!cancelled) setState({ status: "ok", data });
      },
      (error: unknown) => {
        if (!cancelled) setState({ status: "error", error });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [loader, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { state, reload };
}
