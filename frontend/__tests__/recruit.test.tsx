import { render, screen, waitFor } from '@testing-library/react';
import RecruitPage from '@/app/(main)/recruit/page';
import { server } from '@/mocks/server';
import { http, HttpResponse } from 'msw';

// Mock framer-motion to avoid animation related issues in tests
jest.mock('framer-motion', () => {
    const React = require('react');
    return {
        motion: {
            div: React.forwardRef(({ children, ...props }: any, ref: any) => (
                <div {...props} ref={ref}>{children}</div>
            )),
        },
        AnimatePresence: ({ children }: any) => <>{children}</>,
    };
});

// Mock useAuthStore
jest.mock('@/stores/useAuthStore', () => ({
    useAuthStore: () => ({
        isAuthenticated: false,
    }),
}));

// Mock scrollTo
window.scrollTo = jest.fn();

describe('RecruitPage', () => {
    it('renders the hero section and search input', () => {
        render(<RecruitPage />);
        expect(screen.getByText(/당신의 커리어를/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/찾으시는 회사나 직무/i)).toBeInTheDocument();
    });

    it('fetches and displays recruits from the mock API', async () => {
        // Explicitly override with NO delay for this test
        server.use(
            http.get('/api/recruits', () => {
                return HttpResponse.json({
                    items: [
                        { id: 1, title: 'Frontend Developer', company: 'Google', startDate: '2026-02-01', deadline: '2026-03-01', tags: ['React', 'Next.js', 'TypeScript'] }
                    ],
                    meta: { total: 1, page: 1, limit: 10, totalPages: 1 }
                });
            })
        );

        render(<RecruitPage />);

        // Use a longer timeout and check for the content
        await waitFor(() => {
            const elements = screen.queryAllByText(/Frontend Developer/i);
            expect(elements.length).toBeGreaterThan(0);
        }, { timeout: 4000 });
    });

    it('handles API error gracefully', async () => {
        server.use(
            http.get('/api/recruits', () => {
                return new HttpResponse(null, { status: 500 });
            })
        );

        const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { });
        render(<RecruitPage />);

        await waitFor(() => {
            expect(consoleSpy).toHaveBeenCalled();
        });
        consoleSpy.mockRestore();
    });
});
