import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PortfoliosPage from '@/app/(main)/my/portfolios/page';
import React from 'react';

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

describe('PortfoliosPage', () => {
    it('renders the page title and description', () => {
        render(<PortfoliosPage />);
        expect(screen.getByText('내 포트폴리오')).toBeInTheDocument();
        expect(screen.getByText(/등록된 포트폴리오를 관리하고/i)).toBeInTheDocument();
    });

    it('fetches and displays portfolios in grouped format', async () => {
        render(<PortfoliosPage />);

        // Wait for groups to render
        await waitFor(() => {
            // Check for group headers with project counts
            expect(screen.getByText(/나만의 기술 블로그/i)).toBeInTheDocument();
            expect(screen.getByText(/졸업 프로젝트/i)).toBeInTheDocument();
            expect(screen.getByText(/오픈소스 기여 내역/i)).toBeInTheDocument();
        });
    });

    it('displays portfolio groups with project counts', async () => {
        render(<PortfoliosPage />);

        await waitFor(() => {
            // Check that groups show project counts (e.g., "1개 프로젝트")
            const projectCountElements = screen.getAllByText(/개 프로젝트/i);
            expect(projectCountElements.length).toBeGreaterThan(0);
        });
    });

    it('expands group when clicked and shows AI READY badge', async () => {
        render(<PortfoliosPage />);

        // Wait for groups to load
        await waitFor(() => {
            expect(screen.getByText(/나만의 기술 블로그/i)).toBeInTheDocument();
        });

        // Find and click the first group header button
        const groupButtons = screen.getAllByRole('button');
        const firstGroupButton = groupButtons.find(btn =>
            btn.textContent?.includes('나만의 기술 블로그')
        );

        if (firstGroupButton) {
            fireEvent.click(firstGroupButton);

            // After expanding, AI READY badge should be visible
            await waitFor(() => {
                const badges = screen.getAllByText(/AI READY/i);
                expect(badges.length).toBeGreaterThan(0);
            });
        }
    });
});
