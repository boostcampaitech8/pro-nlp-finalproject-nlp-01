export function getApiUrl(path: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
    const prefix = process.env.NEXT_PUBLIC_API_URL_PREFIX || '/api';
    
    // Ensure path starts with / if it's just the endpoint
    const cleanPath = path.startsWith('http') 
        ? path 
        : path.startsWith('/') ? path : `/${path}`;

    // If path is already relative /api/..., just prepend baseUrl
    if (cleanPath.startsWith(prefix)) {
        return `${baseUrl}${cleanPath}`;
    }

    return `${baseUrl}${prefix}${cleanPath}`;
}
