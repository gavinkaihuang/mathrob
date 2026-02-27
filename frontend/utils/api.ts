import { authHeader } from '../context/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
    const headers = {
        ...options.headers,
        ...authHeader() as any, // Cast to avoid TS issues with HeadersInit
    };

    // Check if body is JSON and add content-type if not already set (skip for FormData)
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers,
    });

    // Auto-logout on 401?
    if (res.status === 401) {
        // We could dispatch an event or rely on the AuthContext checking validity
        // Or simply redirect.
        // localStorage.removeItem('access_token');
        // window.location.href = '/login'; 
        // Better to handle this via AuthContext interception or just let the caller verify res.ok
        // But throwing usually helps centralised logic. 
        // For simplicity, just return res and let caller handle, or if we want global 401 handling, do it here.
        if (typeof window !== 'undefined') {
            // Future: Handle redirect
        }
    }

    return res;
}
