import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
    plugins: [react()],
    test: {
        //jsdom simulates a browser env - gives us window, document, localStorage etc
        environment: "jsdom",

        // Run this file before every test file - sets up jset-dom matchers
        // and MSW server lifecycle
        setupFiles: ["./vitest.setup.ts"],

        // Allows using describe/it/expect without importing them in every file
        globals: true,

    },
    resolve:{
        alias: {
            // Mirrors the @/* path alias in tsconfig.json
            "@": path.resolve(__dirname, "./src"),
        },
    },
});