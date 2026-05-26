import { setupServer } from "msw/node";
import { handlers } from "./handlers";

// MSW runs in Node (not the browser) during vitest
// setupServer wires the handlers into Node's http module
export const server = setupServer(...handlers);