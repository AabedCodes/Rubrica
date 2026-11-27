/**
 * Refuses to produce a production bundle that contains the mock API (A1).
 *
 * The mock transport (src/mocks/) answers every §10 route with canned data and
 * accepts a fixed password. It must never ship: a build in "mock" mode would
 * serve a login page that lets anyone in. The app only loads the mock when
 * import.meta.env.MODE === "mock", which is never true in a normal build, and
 * this guard stops anyone running `vite build --mode mock`.
 */
export function assertNoMockInBuild(command: "build" | "serve", mode: string): void {
  if (command === "build" && mode === "mock") {
    throw new Error(
      "Refusing to build in mock mode: the mock API (src/mocks/) must never be shipped. " +
        "Use `npm run dev:mock` for local development instead.",
    );
  }
}
