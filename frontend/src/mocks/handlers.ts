import { http, HttpResponse, delay } from 'msw'

// Mock Data 정의 - 모든 공고의 Master List
const ALL_RECRUITS = [
    { id: 1, title: 'Frontend Developer', company: 'Google', startDate: '2026-02-01', deadline: '2026-03-01', tags: ['React', 'Next.js', 'TypeScript'], isPopular: true },
    { id: 2, title: 'Backend Engineer', company: 'Amazon', startDate: '2026-01-15', deadline: '2026-02-15', tags: ['Java', 'Spring Boot', 'AWS'], isPopular: true },
    { id: 3, title: 'AI Researcher', company: 'OpenAI', startDate: '2026-03-10', deadline: '2026-04-10', tags: ['Python', 'PyTorch', 'LLM'], isRecommended: true, isPopular: true },
    { id: 4, title: 'Product Manager', company: 'Toss', startDate: '2026-01-28', deadline: '2026-02-28', tags: ['Agile', 'Jira', 'Data Analysis'] },
    { id: 5, title: 'DevOps Engineer', company: 'Netflix', startDate: '2026-02-20', deadline: '2026-03-20', tags: ['Kubernetes', 'Terraform', 'Go'], isRecommended: true },
    { id: 6, title: 'Data Scientist', company: 'Kakao', startDate: '2026-02-05', deadline: '2026-03-05', tags: ['Python', 'SQL', 'Hadoop'] },
    { id: 7, title: 'Mobile Developer (iOS)', company: 'Apple', startDate: '2026-02-12', deadline: '2026-03-12', tags: ['Swift', 'SwiftUI', 'Objective-C'] },
    { id: 8, title: 'Security Engineer', company: 'Samsung SDS', startDate: '2026-02-25', deadline: '2026-03-25', tags: ['Network', 'C++', 'Security'] },
    { id: 9, title: 'NLP Research Engineer', company: 'Naver Clova', startDate: '2026-02-15', deadline: '2026-03-15', tags: ['NLP', 'Python', 'HyperCLOVA'], isRecommended: true },
    { id: 10, title: 'LLM Service Developer', company: 'Upstage', startDate: '2026-03-01', deadline: '2026-03-30', tags: ['LangChain', 'Python'], isRecommended: true, isPopular: true },
    { id: 11, title: 'UI/UX Designer', company: 'Line', startDate: '2024-12-01', deadline: '2024-12-31', tags: ['Figma', 'Prototyping'], isPopular: false },
];

const PORTFOLIOS = [
    {
        id: 1,
        title: '나만의 기술 블로그',
        type: 'link',
        url: 'https://velog.io/@test',
        createdAt: '2025-12-01',
        description: '매주 학습한 내용을 기록한 기술 블로그입니다.',
        content: `[주요 포스팅 요약]
- React 렌더링 최적화 전략 (useMemo, useCallback 활용)
- Next.js App Router 전환기: Pages vs App 구조 분석
- 브라우저 렌더링 원리: Critical Rendering Path 이해하기
- lighthouse 성능 지표 90점 이상 달성한 상세 과정`
    },
    {
        id: 2,
        title: '졸업 프로젝트 (PDF)',
        type: 'file',
        createdAt: '2026-01-10',
        description: '학부 졸업 프로젝트 최종 보고서입니다.',
        content: `[멀티 모달 AI 감정 분석 플랫폼]
- 역할: 팀장 및 백엔드 인프라 설계
- 기술: Python, FastAPI, Docker, PyTorch
- 성과: 텍스트와 음성을 동시에 분석하여 92% 정확도 달성
- 특이사항: AWS EC2 환경에서 CI/CD 파이프라인 구축 및 무중단 배포 경험`
    },
    {
        id: 3,
        title: '오픈소스 기여 내역',
        type: 'github',
        url: 'https://github.com/facebook/react',
        createdAt: '2026-01-05',
        description: 'React 리포지토리에 PR을 보낸 내역입니다.',
        content: `[React 공식 레포지토리 기여]
- PR 제목: Fix memory leak in useEffect cleanup (merged)
- 내용: 특정 Edge case에서 cleanup 함수가 누락되어 메모리 릭이 발생하는 버그 수정
- 영향: 전 세계 수만 개의 React 프로젝트 안정성 향상에 기여`
    },
];

let COVER_LETTERS = [
    {
        id: 1,
        title: '구글 2026 상반기 지원',
        content: '구글의 비전에 깊이 공감하며...',
        questions: [
            { id: 1, question: "지원동기", answer: "구글의 비전에 깊이 공감하며..." },
            { id: 2, question: "성장과정", answer: "어릴 때부터..." }
        ],
        recruitId: 1,
        updatedAt: '2026-01-15'
    },
    {
        id: 3,
        title: '[작성중] 아마존 백엔드 엔지니어',
        content: 'AWS 클라우드 경험을 바탕으로...',
        questions: [
            { id: 1, question: "자기소개", answer: "AWS 클라우드 경험을 바탕으로..." }
        ],
        recruitId: 2,
        updatedAt: '2026-01-16'
    },
    {
        id: 4,
        title: '[임시저장] 토스 PM 지원',
        content: '토스의 금융 혁신에...',
        questions: [
            { id: 1, question: "지원동기", answer: "토스의 금융 혁신에..." }
        ],
        recruitId: 4,
        updatedAt: '2026-01-14'
    },
    {
        id: 5,
        title: '라인 UI/UX 디자인 지원 (마감)',
        content: '사용자 경험을 최우선으로...',
        questions: [
            { id: 1, question: "지원동기", answer: "사용자 경험을 최우선으로..." }
        ],
        recruitId: 11,
        updatedAt: '2024-12-25'
    },
];

export const handlers = [
    // AI 포트폴리오 분석 및 생성 시뮬레이션
    http.post('*/api/portfolios/analyze', async ({ request }) => {
        let source = 'Unknown';
        let type = 'link';
        try {
            const body = await request.json() as { source?: string; type?: string };
            source = body.source || source;
            type = body.type || type;
        } catch (e) {
            console.warn('[MSW] Analyze handler failed to parse body:', e);
        }

        await delay(1000);

        const generated = [
            {
                id: Date.now() + 1,
                title: `${source} 기반 프로젝트 A`,
                type: type === 'github' ? 'github' : 'link',
                description: 'AI가 추출한 프로젝트의 핵심 설명입니다.',
                content: '- 주요 성과: 성능 20% 개선\n- 활용 기술: React, Node.js\n- 상세 내용: 대규모 트래픽 처리를 위한 아키텍처 설계 및 구현',
                createdAt: new Date().toISOString().split('T')[0]
            },
            {
                id: Date.now() + 2,
                title: `${source} 기반 프로젝트 B`,
                type: type === 'github' ? 'github' : 'file',
                description: '데이터 시각화 및 대시보드 구축 경험입니다.',
                content: '- 주요 성과: 가시성 확보로 의사결정 속도 향상\n- 활용 기술: D3.js, TypeScript\n- 상세 내용: 복잡한 데이터셋을 한눈에 파악할 수 있는 인터랙티브 차트 구현',
                createdAt: new Date().toISOString().split('T')[0]
            }
        ];

        return HttpResponse.json(generated);
    }),

    // 로그인
    http.post('/api/auth/login', async () => {
        return HttpResponse.json({
            user: { id: 1, email: 'test@example.com', name: '김코딩' },
            token: 'mock-jwt-token'
        })
    }),

    // 회원가입
    http.post('/api/auth/signup', async () => {
        return HttpResponse.json({
            success: true,
            message: '회원가입이 완료되었습니다.'
        })
    }),

    // 프로필 조회
    http.get('/api/auth/me', () => {
        return HttpResponse.json({
            id: 1,
            email: 'test@example.com',
            name: '김코딩'
        })
    }),

    // 전체 채용 공고 리스트
    http.get('/api/recruits', () => {
        return HttpResponse.json(ALL_RECRUITS)
    }),

    // 전체 채용 공고 리스트 (필터링, 검색, 페이지네이션 지원)
    http.get('/api/recruits', ({ request }) => {
        const url = new URL(request.url)
        const page = parseInt(url.searchParams.get('page') || '1')
        const limit = parseInt(url.searchParams.get('limit') || '10')
        const category = url.searchParams.get('category')
        const techStack = url.searchParams.get('techStack')
        const keyword = url.searchParams.get('keyword')
        const sort = url.searchParams.get('sort')

        let filtered = [...ALL_RECRUITS]

        // 카테고리 필터링 (Mock 데이터 제목/태그 기반 시뮬레이션)
        if (category && category !== 'all') {
            filtered = filtered.filter(r => {
                const title = r.title.toLowerCase()
                const tags = r.tags.map(t => t.toLowerCase())
                if (category === 'frontend') return title.includes('frontend') || tags.includes('react')
                if (category === 'backend') return title.includes('backend') || tags.includes('spring')
                if (category === 'ai') return title.includes('ai') || title.includes('nlp')
                return true
            })
        }

        // 기술 스택 필터링
        if (techStack) {
            const techs = techStack.split(',').map(t => t.toLowerCase())
            filtered = filtered.filter(r =>
                techs.every(t => r.tags.some(tag => tag.toLowerCase().includes(t)))
            )
        }

        // 키워드 검색
        if (keyword) {
            const q = keyword.toLowerCase()
            filtered = filtered.filter(r =>
                r.title.toLowerCase().includes(q) || r.company.toLowerCase().includes(q)
            )
        }

        // 정렬
        if (sort === 'popular') {
            filtered.sort((a, b) => (b.isPopular ? 1 : 0) - (a.isPopular ? 1 : 0))
        }

        const total = filtered.length
        const totalPages = Math.ceil(total / limit)
        const rawItems = filtered.slice((page - 1) * limit, page * limit)

        // 데이터 클렌징: isPopular, isRecommended 필드 제거
        const items = rawItems.map(({ isPopular: _isPopular, isRecommended: _isRecommended, ...rest }) => rest)

        return HttpResponse.json({
            items,
            meta: { total, page, limit, totalPages }
        })
    }),

    // 추천 공고 리스트 (추천 플래그 + 필터링 지원)
    http.get('/api/recruits/recommend', ({ request }) => {
        const url = new URL(request.url)
        const page = parseInt(url.searchParams.get('page') || '1')
        const limit = parseInt(url.searchParams.get('limit') || '9')

        const recommended = ALL_RECRUITS.filter(r => r.isRecommended);

        const total = recommended.length
        const totalPages = Math.ceil(total / limit)
        const rawItems = recommended.slice((page - 1) * limit, page * limit)

        // 내부용 플래그 제거
        const items = rawItems.map(({ isPopular: _isPopular, isRecommended: _isRecommended, ...rest }) => rest)

        return HttpResponse.json({
            items,
            meta: { total, page, limit, totalPages }
        })
    }),

    // 포트폴리오 리스트 (페이지네이션 추가)
    http.get('/api/portfolios', ({ request }) => {
        const url = new URL(request.url)
        const page = parseInt(url.searchParams.get('page') || '1')
        const limit = parseInt(url.searchParams.get('limit') || '10')

        const total = PORTFOLIOS.length
        const totalPages = Math.ceil(total / limit)
        const items = PORTFOLIOS.slice((page - 1) * limit, page * limit)

        return HttpResponse.json({
            items,
            meta: { total, page, limit, totalPages }
        })
    }),

    // 포트폴리오 생성
    http.post('/api/portfolios', async ({ request }) => {
        const data = await request.json() as Record<string, unknown>;
        const newPortfolio = {
            ...data,
            id: Date.now(),
            createdAt: new Date().toISOString().split('T')[0]
        };
        PORTFOLIOS.push(newPortfolio as typeof PORTFOLIOS[0]);
        return HttpResponse.json(newPortfolio);
    }),

    // 포트폴리오 상세
    http.get('/api/portfolios/:id', ({ params }) => {
        const { id } = params
        const portfolio = PORTFOLIOS.find(p => p.id === Number(id))

        if (!portfolio) {
            return new HttpResponse(null, { status: 404 })
        }

        return HttpResponse.json(portfolio)
    }),

    // 포트폴리오 업데이트
    http.patch('/api/portfolios/:id', async ({ request, params }) => {
        const { id } = params;
        const data = await request.json() as Record<string, unknown>;
        const index = PORTFOLIOS.findIndex(p => p.id === Number(id));
        if (index !== -1) {
            PORTFOLIOS[index] = { ...PORTFOLIOS[index], ...data } as typeof PORTFOLIOS[0];
            return HttpResponse.json(PORTFOLIOS[index]);
        }
        return new HttpResponse(null, { status: 404 });
    }),

    // 포트폴리오 삭제
    http.delete('/api/portfolios/:id', ({ params }) => {
        const { id } = params;
        const index = PORTFOLIOS.findIndex(p => p.id === Number(id));
        if (index !== -1) {
            PORTFOLIOS.splice(index, 1);
            return HttpResponse.json({ success: true });
        }
        return new HttpResponse(null, { status: 404 });
    }),

    // 자소서 리스트 (필터링 및 페이지네이션)
    http.get('/api/cover-letters', ({ request }) => {
        const url = new URL(request.url);
        const recruitId = url.searchParams.get('recruitId');
        const page = parseInt(url.searchParams.get('page') || '1');
        const limit = parseInt(url.searchParams.get('limit') || '10');

        // 데이터 매핑 (Join)
        const enrichedCoverLetters = COVER_LETTERS.map(cl => {
            const recruit = ALL_RECRUITS.find(r => r.id === cl.recruitId);
            return {
                ...cl,
                recruitTitle: recruit?.title,
                recruitCompany: recruit?.company,
                recruitDeadline: recruit?.deadline
            };
        });

        let filtered = enrichedCoverLetters;
        if (recruitId) {
            filtered = filtered.filter(cl => cl.recruitId === Number(recruitId));
        }

        const total = filtered.length;
        const totalPages = Math.ceil(total / limit);
        const items = filtered.slice((page - 1) * limit, page * limit);

        return HttpResponse.json({
            items,
            meta: { total, page, limit, totalPages }
        });
    }),

    // 자소서 상세 조회
    http.get('/api/cover-letters/:id', ({ params }) => {
        const { id } = params
        const cl = COVER_LETTERS.find(c => c.id === Number(id));
        if (!cl) {
            return HttpResponse.json({
                id: Number(id),
                title: '제목 없음',
                content: '',
                questions: [],
                recruitId: 0,
                updatedAt: '2026-01-01'
            })
        }
        return HttpResponse.json(cl)
    }),

    // 자소서 생성/저장 (Mock)
    http.post('/api/cover-letters', async ({ request }) => {
        const data = await request.json() as Record<string, unknown>;
        const newLetter = {
            ...data,
            id: Date.now(),
            updatedAt: new Date().toISOString().split('T')[0]
        };
        COVER_LETTERS.push(newLetter as typeof COVER_LETTERS[0]);
        return HttpResponse.json(newLetter);
    }),

    // 자소서 업데이트 (Mock)
    http.patch('/api/cover-letters/:id', async ({ request, params }) => {
        const { id } = params;
        const data = await request.json() as Record<string, unknown>;
        COVER_LETTERS = COVER_LETTERS.map(cl => cl.id === Number(id) ? { ...cl, ...data } as typeof COVER_LETTERS[0] : cl);
        return HttpResponse.json({ success: true });
    }),

    // 자소서 삭제 (Mock)
    http.delete('/api/cover-letters/:id', ({ params }) => {
        const { id } = params;
        COVER_LETTERS = COVER_LETTERS.filter(cl => cl.id !== Number(id));
        return HttpResponse.json({ success: true });
    }),

    // AI 자소서 생성 API (Core AI Logic Mock)
    http.post('/api/cover-letters/generate', async ({ request }) => {
        const { mode, tone, focus, portfolioIds, question } = await request.json() as {
            mode?: string;
            tone?: string;
            focus?: string;
            portfolioIds: number[];
            question?: string;
        };

        await delay(1500); // AI 분석 연출을 위한 딜레이

        const selectedPfs = PORTFOLIOS.filter(p => portfolioIds.includes(p.id));
        const pfHighlights = selectedPfs.map(p => {
            const lines = p.content?.split('\n').filter(l => l.startsWith('-')) || [];
            return lines.length > 0 ? lines[0].replace('- ', '') : p.title;
        }).join(', ');

        if (mode === 'strategy') {
            return HttpResponse.json({
                result: `[전략 가제안: ${question}]\n\n1. 핵심 가치: ${focus || '성과 중심의 전문성'}\n2. 활용 데이터: ${pfHighlights}\n3. 서술 흐름:\n   - 도입: ${selectedPfs[0]?.title}에서의 주요 성과를 통한 강점 어필\n   - 본문: 구체적인 기술 스택 및 성과(${pfHighlights})를 강조하며 실질적 기여도 서술 (Tone: ${tone})\n   - 결론: 기업의 성장 방향과 나의 전문성 정렬\n4. 추천 키워드: 전문성, 문제해결력, ${pfHighlights.split(' ')[0]}`
            });
        }

        if (mode === 'refine') {
            return HttpResponse.json({
                result: `기존 메모를 포트폴리오 데이터 기반으로 ${tone}하게 정밀화한 결과입니다:\n\n"저는 ${pfHighlights} 경험을 통해 실전형 역량을 쌓았습니다. 특히 ${focus || '본 프로젝트'} 과정에서 발생한 문제를 기술적으로 해결한 경험이 있으며, 이는 귀사에서도..."`
            });
        }

        // Default: Draft mode
        return HttpResponse.json({
            result: `[AI 생성 초안]\n\n질문: ${question}\n\n저는 ${pfHighlights} 등 다양한 프로젝트를 통해 탄탄한 기본기를 다져왔습니다. 특히 ${selectedPfs[0]?.title}를 진행하며 다음과 같은 역량을 입증했습니다.\n\n해당 과정에서 ${pfHighlights}와 같은 핵심 과업을 성공적으로 완수하며 팀의 목표 달성에 기여했습니다. ${focus}\n\n이러한 저의 ${tone}한 자세는 귀사가 지향하는 가치와 맞닿아 있으며...`
        });
    }),

    // 상세 조회 Mock (전체 리스트에서 검색)
    http.get('/api/recruits/:id', ({ params }) => {
        const { id } = params
        const idNum = Number(id);

        const recruit = ALL_RECRUITS.find(r => r.id === idNum);

        if (!recruit) {
            return HttpResponse.json({
                id: idNum,
                title: 'Software Engineer',
                company: 'Unknown Company',
                deadline: '2026-12-31',
                tags: ['General'],
                content: `해당 공고를 찾을 수 없지만, 예시 데이터를 보여드립니다.\n\n[기업 소개]\n혁신적인 기술로 세상을 바꿉니다.\n\n[주요 업무]\n- 서비스 개발 및 운영`
            })
        }

        return HttpResponse.json({
            ...recruit,
            content: `${recruit.company}에서 역량 있는 인재를 모십니다.\n\n[기업 소개]\n${recruit.company}는 글로벌 시장을 선도하는 기업입니다. 우리는 기술을 통해 더 나은 세상을 만듭니다.\n\n[주요 업무]\n- ${recruit.tags.join(', ')} 기반 대규모 트래픽 처리 시스템 설계 및 구축\n- 사용자 중심의 서비스 개발 및 성능 최적화\n- 데이터 기반의 의사결정 및 제품 개선\n\n[자격 요건]\n- 해당 직무 관련 경험 3년 이상\n- 능동적인 커뮤니케이션 스킬 보유자\n- 새로운 기술 학습에 대한 열정\n\n[우대 사항]\n- 오픈소스 기여 경험\n- 클라우드 환경(AWS, GCP) 구축 경험`
        })
    }),
]
