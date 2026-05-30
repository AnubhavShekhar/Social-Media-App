import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
}));

const mockSetUser = vi.fn();
vi.mock("@/lib/auth-context", () => ({
    useAuth : () => ({ user: null, setUser: mockSetUser }),
}));

import SignupPage from "@/app/signup/page";

describe("SignupPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    // ----- Rendering ----------------------------------------

    it("renders email, password and confirm password fields", () => {
        render(<SignupPage/>);
        expect(screen.getByLabelText("Email")).toBeInTheDocument();
        expect(screen.getByLabelText("Password")).toBeInTheDocument();
        expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
    });

    it("renders the create account button", () => {
        render(<SignupPage/>);
        expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
    });

    it("renders a link to the login page", () => {
        render(<SignupPage/>);
        expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute(
            "href",
            "/login"
        );
    });

    // --------- Client side validation -----------------------------

    it("shows error when passwords do not match", async () => {
        const user = userEvent.setup();
        render(<SignupPage/>);

        await user.type(screen.getByLabelText("Email"), "test@example.com");
        await user.type(screen.getByLabelText("Password"), "password123");
        await user.type(screen.getByLabelText("Confirm Password"), "different");
        await user.click(screen.getByRole("button", { name: /create account/i }));

        expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
        // No API call should be made - validation runs before fetch
        expect(mockPush).not.toHaveBeenCalled();
    });

    // -------- Successful signup -----------------------------

    it("stores token, sets user and redirects to /home on success", async () => {
        const user = userEvent.setup();
        render(<SignupPage/>);
        
        await user.type(screen.getByLabelText("Email"), "test@example.com");
        await user.type(screen.getByLabelText("Password"), "password123");
        await user.type(screen.getByLabelText("Confirm Password"), "password123");
        await user.click(screen.getByRole("button", { name: /create account/i }));

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
            http.post("http://localhost:8000/signup", async () => {
                await new Promise((resolve) => setTimeout(resolve, 100));
                return HttpResponse.json({
                    access_token: "fake_jwt_token",
                    token_type: "bearer",
                    expires_in: 1800,
                });
            })
        );

        const user = userEvent.setup();
        render(<SignupPage />);

        await user.type(screen.getByLabelText("Email"), "test@example.com");
        await user.type(screen.getByLabelText("Password"), "password123");
        await user.type(screen.getByLabelText("Confirm Password"), "password123");

        const clickPromise = user.click(screen.getByRole("button", { name: /create account/i }));

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /creating account/i })).toBeDisabled();
        });

        await clickPromise;
    }); 

    // -------- Failed signup --------------------------------

    it("shows error message when email is already taken", async () => {
        server.use(
            http.post("http://localhost:8000/users", () => 
            HttpResponse.json(
                { detail: "User with this email already exists" },
                { status: 409 }
            ))
        );

        const user = userEvent.setup({ delay: null });
        render(<SignupPage/>);

        await user.type(screen.getByLabelText("Email"), "taken@example.com");
        await user.type(screen.getByLabelText("Password"), "password123");
        await user.type(screen.getByLabelText("Confirm Password"), "password123");
        
        mockPush.mockClear();
        await user.click(screen.getByRole("button", { name: /create account/i }));

        await waitFor(() => {
            expect(screen.getByText("User with this email already exists")).toBeInTheDocument();
        });
        
        expect(mockPush).not.toHaveBeenCalled();
   });

   it("re-enables submit button after a failed signup", async () => {
        server.use(
            http.post("http://localhost:8000/users", () =>
            HttpResponse.json(
                { detail: "User with this email already exists" },
                { status: 409 }
            ))
        );

        const user = userEvent.setup({ delay: null });
        render(<SignupPage/>);

        await user.type(screen.getByLabelText("Email"), "taken@example.com");
        await user.type(screen.getByLabelText("Password"), "password123");
        await user.type(screen.getByLabelText("Confirm Password"), "password123");
        
        mockPush.mockClear();
        await user.click(screen.getByRole("button", { name: /create account/i }));

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /create account/i })).not.toBeDisabled();
        });
   });
});