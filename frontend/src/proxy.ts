import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
    const { pathname } = request.nextUrl

    // 1. 공개 경로 확인 (루트, 로그인/회원가입, 채용공고는 누구나 접근 가능)
    const isPublicPath =
        pathname === '/' ||
        pathname === '/login' ||
        pathname === '/signup' ||
        pathname === '/favicon.ico' ||
        pathname.startsWith('/recruit') ||
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
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * - files with extension (images, fonts, etc.)
         */
        '/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)',
    ],
}
