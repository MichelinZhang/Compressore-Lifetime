import { describe, expect, it } from "vitest";

import { ApiError, toErrorMessage } from "./errors";

describe("toErrorMessage", () => {
  it("formats ApiError with status and detail", () => {
    const msg = toErrorMessage(new ApiError(400, "Bad Request"));
    expect(msg).toBe("400: Bad Request");
  });

  it("formats standard Error", () => {
    const msg = toErrorMessage(new Error("boom"));
    expect(msg).toBe("boom");
  });

  it("formats plain object", () => {
    const msg = toErrorMessage({ code: 1, message: "oops" });
    expect(msg).toContain("\"code\":1");
  });
});

