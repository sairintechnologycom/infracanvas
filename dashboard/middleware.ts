import { NextResponse, type NextRequest } from 'next/server'
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher([
  '/share(.*)',
  '/sign-in(.*)',
  '/sign-up(.*)',
])

const DEV_BYPASS = process.env.DEV_BYPASS_AUTH === '1'

const productionMiddleware = clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect()
  }
})

export default DEV_BYPASS
  ? function bypassMiddleware(_req: NextRequest) {
      return NextResponse.next()
    }
  : productionMiddleware

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
