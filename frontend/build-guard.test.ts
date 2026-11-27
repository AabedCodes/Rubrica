import { describe, expect, it } from "vitest";
import { assertNoMockInBuild } from "./build-guard";

describe("build guard (A1)", () => {
  it("refuses a production build in mock mode", () => {
    expect(() => assertNoMockInBuild("build", "mock")).toThrow(/mock mode/);
  });

  it("allows a normal build and the mock dev server", () => {
    expect(() => assertNoMockInBuild("build", "production")).not.toThrow();
    expect(() => assertNoMockInBuild("serve", "mock")).not.toThrow();
  });
});
