"use client";

import {
    createContext,
    useContext,
    useEffect,
    useState,
    ReactNode,
    useMemo,
} from "react";
import { getMe } from "@/lib/api";
import type { User } from "@/lib/api";

// ------The shape of what the context holds ----------------------------

interface AuthContextValue {
    user : User | null;
    loading : boolean;
    setUser : (user : User | null) => void;
    logout : () => void;
}

// ---------Create the context with a default value ---------------------

const AuthContext = createContext<AuthContextValue>({
    user : null,
    loading : true,
    setUser : () => {},
    logout : () => {},
})

//----------The provider component ----------------------------------------

export function AuthProvider({ children }: Readonly<{ children : ReactNode}>){
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    // When the app first loads, check if there's a token already in local storage 
    // and if so fetch the current user so they don't have to login again

    useEffect(() => {
        const token = localStorage.getItem("access_token");

        async function restoreSession() {
            if (!token) return;
            try {
                const me = await getMe();
                setUser(me);
            } catch {
                localStorage.removeItem("access_token");
            } finally {
                setLoading(false);
            }
        }

        restoreSession();
    }, []);

    function logout() {
        localStorage.removeItem("access_token");
        setUser(null);
    }

    const value = useMemo(
        () => ({ user, loading, setUser, logout }),
        [user, loading]
    );

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// -------The hook that components use to access auth state--------------

export function useAuth() {
    return useContext(AuthContext);
}