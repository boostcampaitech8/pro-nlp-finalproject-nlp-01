"use client";

import "@testing-library/jest-dom";
import { render, screen, waitFor } from '@testing-library/react';
import PortfoliosPage from "../src/app/(main)/my/portfolios/page";
import { ToastProvider } from "../src/components/ui/toast-context";
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
    it('renders the page title and description', async () => {
        render(
            <ToastProvider>
                <PortfoliosPage />
            </ToastProvider>
        );

        await waitFor(() => {
            expect(screen.getByText("내 포트폴리오")).toBeInTheDocument();
        });
        expect(screen.getByText(/등록된 포트폴리오를 관리하고/i)).toBeInTheDocument();
    });

    it('fetches and displays portfolios as individual cards', async () => {
        render(
            <ToastProvider>
                <PortfoliosPage />
            </ToastProvider>
        );

        // Wait for items to render
        await waitFor(() => {
            // Use getAllByText and check length to avoid ambiguity with descriptions
            expect(screen.getAllByText(/나만의 기술 블로그/i).length).toBeGreaterThan(0);
            expect(screen.getAllByText(/졸업 프로젝트/i).length).toBeGreaterThan(0);
            expect(screen.getAllByText(/오픈소스 기여 내역/i).length).toBeGreaterThan(0);
        });
    });

    it('displays portfolio cards with AI READY badge', async () => {
        render(
            <ToastProvider>
                <PortfoliosPage />
            </ToastProvider>
        );

        await waitFor(() => {
            expect(screen.getAllByText(/나만의 기술 블로그/i).length).toBeGreaterThan(0);

            // Check for AI READY badge (should be visible by default, no expansion needed)
            const badges = screen.getAllByText(/AI READY/i);
            expect(badges.length).toBeGreaterThan(0);
        });
    });
});
