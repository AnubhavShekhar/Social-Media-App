import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";

// ------- Mock next/navigation ------------------------------
// useRouter is called at the top of the LoginPage. Without this mock vitest 
// throws because there is no Next.js App router context in jsdom

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
    useRouter: () => ({ push : mockPush }),
}));

// ------ Moch useAuth -----------------------------------------
// We mock the module so the component gets a controlled setUser spy instead
// of the real AuthProvider (which would fire getMe fetch on mount)

const mockSetUser = vi.fn();
vi.mock("@/lib/auth-context", () => ({
    useAuth: () => ({ user: null, setUser: mockSetUser }),
}));

import LoginPage from "@/app/login/page";

describe("LoginPage", () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        localStorage.clear();
        // Let any pending promises from the previous tests settle
        await new Promise((resolve) => setTimeout(resolve, 0));
    });

    // --------- Rendering --------------------------
    it("renders the email and password fields", () => {
        render(<LoginPage/>);
        expect(screen.getByLabelText("Email")).toBeInTheDocument();
        expect(screen.getByLabelText("Password")).toBeInTheDocument();
    });

    it("renders the sign in button", () => {
        render(<LoginPage/>);
        expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });

    it("renders a link to the signup page", () => {
        render(<LoginPage/>);
        expect(screen.getByRole("link", { name: /create one/i })).toHaveAttribute(
            "href",
            "/signup"
        );
    });

    // ---- Successful login ----------------------------------------

    it("stores the token and redirects to /home on success", async () => {
        const user = userEvent.setup();
        render(<LoginPage/>);

        await user.type(screen.getByLabelText("Email"), "test@example.com");
        await user.type(screen.getByLabelText("Password"), "password123");
        await user.click(screen.getByRole("button", { name: /sign in/i }));

        await waitFor(() => {
            expect(localStorage.getItem("access_token")).toBe("fake_jwt_token");
            expect(mockSetUser).toHaveBeenCalledWith(
                expect.objectContaining({ email: "test@example.com" })
            );
            expect(mockPush).toHaveBeenCalledWith("/home");
        });
    });

   it("disables submit button while request is in flight", async () => {
    // Make the response artificially slow so we can assert mid-flight
    server.use(
        http.post("http://localhost:8000/login", async () => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            return HttpResponse.json({
                access_token: "fake_jwt_token",
                token_type: "bearer",
                expires_in: 1800,
            });
        })
    );

    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");

    const clickPromise = user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
        expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
    });

    await clickPromise;
}); 

    // ------------ Failed login ---------------------------------

    it("shows error message on invalid credentials", async () => {
        // Overrides the default handler to return 401 for this test only
        server.use(
            http.post("http://localhost:8000/login", () => 
            HttpResponse.json(
                { detail : "Invalid credentials" },
                { status : 401 }
            ))
        );

        const user = userEvent.setup();
        render(<LoginPage/>);

        await user.type(screen.getByLabelText("Email"), "wrong@example.com");
        await user.type(screen.getByLabelText("Password"), "wrongpassword");

        mockPush.mockClear();
        await user.click(screen.getByRole("button", { name: /sign in/i }));

        await waitFor(() => {
            expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
        });

        // Must not redirect on failure
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("re-enables the submit button after a failed login", async () => {
        server.use(
            http.post("http://localhost:8000/login", () => 
                HttpResponse.json({ detail : "Invalid credentials"}, { status: 401 })
            )
        );

        const user = userEvent.setup();
        render(<LoginPage/>);

        await user.type(screen.getByLabelText("Email"), "a@b.com");
        await user.type(screen.getByLabelText("Password"), "wrong");
        await user.click(screen.getByRole("button", { name : /sign in/i }));

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /sign in/i })).not.toBeDisabled();
        });
    });
});