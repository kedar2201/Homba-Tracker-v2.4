import axios from "axios";

const api = axios.create({
    baseURL: '/api',
    timeout: 60000,
});

// Add a request interceptor to add the auth token to every request
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("token");
        if (token) {
            // Trim whitespace to avoid "Not enough segments" errors
            config.headers.Authorization = `Bearer ${token.trim()}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add a response interceptor to handle errors globally 
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            localStorage.removeItem("token");

            // Avoid infinite redirect or clearing error messages if handled locally
            const isAuthRequest = error.config.url.includes('/auth/token');
            const isAlreadyOnLogin = window.location.pathname === "/login";

            if (!isAuthRequest && !isAlreadyOnLogin) {
                window.location.href = "/login";
            }
        }
        return Promise.reject(error);
    }
);


export const getCurrentUser = async () => {
    const response = await api.get('/auth/me');
    return response.data;
};

export const getAnalytics = async (symbol: string) => {
    const response = await api.get(`/analytics/${symbol}`);
    return response.data;
};

export const updateEps = async (symbol: string, eps: number) => {
    const response = await api.post('/analytics/eps', { symbol, eps });
    return response.data;
};

export const refreshAnalytics = async (symbol: string) => {
    const response = await api.post(`/analytics/refresh/${symbol}`);
    return response.data;
};

export const updateGrowthRate = async (symbol: string, growth: number) => {
    const response = await api.post('/analytics/growth', { symbol, growth });
    return response.data;
};

export const updateYahooSymbol = async (symbol: string, yahoo_symbol: string, locked: boolean = false) => {
    const response = await api.post('/analytics/yahoo-symbol', { symbol, yahoo_symbol, locked });
    return response.data;
};

export const getAllRatings = async () => {
    const response = await api.get('/rating/all');
    return response.data;
};

export const getRating = async (symbol: string) => {
    const response = await api.get(`/rating/${symbol}`);
    return response.data;
};

export const computeRating = async (symbol: string) => {
    const response = await api.post(`/rating/compute/${symbol}`);
    return response.data;
};

export default api;



