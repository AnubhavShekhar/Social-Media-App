import "@testing-library/jest-dom";
import { beforeAll, afterEach, afterAll } from "vitest";
import { server } from "@/tests/msw/server";

// Start the MSW server before all tests in the suite.
// onUnhandledRequest: 'error' makes the test fail if a request is made that
// has no matching handler - catches accidental real network calls early

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

// Reset handlers after each test so one test's ovverides don't bleed into
// the next. Individual tests can add handlers via server.use() safely
afterEach(() => server.resetHandlers());

// Shut down the server after the entire suite finishes
afterAll(() => server.close());