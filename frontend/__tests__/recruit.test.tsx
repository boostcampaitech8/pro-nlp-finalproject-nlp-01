import { render, screen, waitFor } from '@testing-library/react';
import RecruitPage from '@/app/(main)/recruit/page';
import { server } from '@/mocks/server';
import { http, HttpResponse } from 'msw';

// Mock framer-motion to avoid animation related issues in tests
jest.mock('framer-motion', () => {
    const React = require('react'); // eslint-disable-line @typescript-eslint/no-require-imports

    interface MockProps {
        children?: React.ReactNode;
        [key: string]: unknown;
    }

    const MockDiv = React.forwardRef(({ children, ...props }: MockProps, ref: React.Ref<HTMLDivElement>) => (
        <div {...props} ref={ref}>{children}</div>
    ));
    MockDiv.displayName = 'MotionDiv';

    return {
        motion: {
            div: MockDiv,
        },
        AnimatePresence: ({ children }: MockProps) => <>{children}</>,
    };
});

jest.mock('@/stores/useAuthStore', () => {
    const mockStore = {
        isAuthenticated: false,
        token: null,
        getState: () => ({
            isAuthenticated: false,
            token: null,
            logout: jest.fn(),
        }),
    };
    return {
        useAuthStore: Object.assign(() => mockStore, mockStore),
    };
});

// Mock Tooltip component to avoid Radix UI dependency issues in tests
jest.mock('@/components/ui/tooltip', () => ({
    Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock scrollTo
window.scrollTo = jest.fn();

describe('RecruitPage', () => {
    it('renders the hero section and search input', () => {
        render(<RecruitPage />);
        expect(screen.getByText(/당신의 커리어를/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/회사, 직무, 기술 스택 검색/i)).toBeInTheDocument();
    });

    it('fetches and displays recruits from the mock API', async () => {
        // Explicitly override with NO delay for this test
        server.use(
            http.get('/api/recruits', () => {
                return HttpResponse.json({
                    items: [
                        { id: 1, title: 'Frontend Developer', company: 'Google', start_date: '2026-02-01', deadline: '2026-03-01', tags: ['React', 'Next.js', 'TypeScript'] }
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
