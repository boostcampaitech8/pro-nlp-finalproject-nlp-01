import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
    const { pathname } = request.nextUrl
    const host = request.headers.get('host');
    const productionDomain = 'pro-nlp-finalproject-nlp-01.vercel.app';

    // 0. 도메인 체크 (Preview URL 허용, 그 외의 커스텀 도메인이나 예전 배포만 메인으로 리다이렉트)
    // Vercel Preview URL은 보통 '*-git-*.vercel.app' 형태이므로 'vercel.app'을 포함하면 허용합니다.
    if (
        process.env.NODE_ENV === 'production' &&
        host &&
        host !== productionDomain &&
        !host.includes('localhost') &&
        !host.includes('127.0.0.1') &&
        !host.endsWith('.vercel.app') // Vercel Preview 도메인은 허용
    ) {
        const url = request.nextUrl.clone();
        url.host = productionDomain;
        url.protocol = 'https:';
        return NextResponse.redirect(url, 307);
    }

    // 1. 공개 경로 확인 (루트, 로그인/회원가입, 채용공고는 누구나 접근 가능)
    const isPublicPath =
        pathname === '/' ||
        pathname === '/login' ||
        pathname === '/signup' ||
        pathname === '/favicon.ico' ||
        pathname.startsWith('/recruit') ||
        pathname.startsWith('/auth/kakao') ||
        pathname.startsWith('/api');

    if (isPublicPath) {
        return NextResponse.next()
    }

    // 2. 인증 토큰 확인
    const hasToken = request.cookies.has('accessToken')

    if (!hasToken) {
        const url = request.nextUrl.clone()
        url.pathname = '/login'
        return NextResponse.redirect(url)
    }

    return NextResponse.next()
}

export const config = {
    matcher: [
        /*
         * 1. 다음으로 시작하는 경로는 모두 제외 (최우선)
         * - api, _next/static, _next/image, favicon.ico, sitemap, robots
         */
        '/((?!api|_next/static|_next/image|favicon.ico|sitemap|robots|.*\\..*).*)',

        /* 
         * 2. 혹은 좀 더 보수적으로 특정 경로 그룹만 지정하는 방식도 가능합니다.
         * 여기서는 위 방식을 유지하되 불필요한 실행을 내부 로직에서 한 번 더 거릅니다.
         */
    ],
}
