import { render, screen, waitFor } from '@testing-library/react';
import RecruitPage from '@/app/(main)/recruit/page';
import { useAuthStore } from '@/stores/useAuthStore';

// Next.js Link와 Framer Motion 등의 모킹이 필요할 수 있습니다.
jest.mock('next/link', () => {
    return ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    );
});

describe('RecruitPage Integration Test with MSW', () => {
    it('채용 공고 목록이 Mock 데이터를 통해 정상적으로 렌더링되는지 확인합니다.', async () => {
        render(<RecruitPage />);

        // 로딩 상태 확인 (Skeleton 또는 로딩 텍스트가 없어질 때까지 대기)
        await waitFor(() => {
            // handlers.ts에 정의된 ALL_RECRUITS 중 하나가 화면에 나타나는지 확인
            // 예: "프론트엔드" 또는 Mock 데이터에 포함된 회사명
            expect(screen.queryByTestId('loading-skeleton')).toBeNull();
        }, { timeout: 3000 });

        // 최소한 하나의 공고 카드가 렌더링되었는지 확인
        // (참고: handlers.ts에서 반환하는 실제 텍스트로 수정이 필요할 수 있음)
        const recruitItems = await screen.findAllByRole('heading', { level: 3 });
        expect(recruitItems.length).toBeGreaterThan(0);
    });

    it('인증되지 않은 사용자가 맞춤 추천 탭 클릭 시 로그인 안내가 표시되는지 확인합니다.', async () => {
        // 비로그인 상태 강제 설정
        useAuthStore.setState({ isAuthenticated: false });

        render(<RecruitPage />);

        const recommendTab = screen.getByText(/맞춤 추천/i);
        recommendTab.click();

        await waitFor(() => {
            expect(screen.getByText(/로그인이 필요합니다/i)).toBeInTheDocument();
        });
    });
});
