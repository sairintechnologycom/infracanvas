import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock backendFetch before importing the route
vi.mock('@/lib/backend', () => ({
  backendFetch: vi.fn(),
}))

import { backendFetch } from '@/lib/backend'
import { PATCH } from './route'

describe('PATCH /api/integrations/slack proxy', () => {
  beforeEach(() => vi.clearAllMocks())

  it('returns 200 with message on backend success', async () => {
    vi.mocked(backendFetch).mockResolvedValueOnce({ message: 'Slack webhook saved' })
    const req = new Request('http://localhost/api/integrations/slack', {
      method: 'PATCH',
      body: JSON.stringify({ webhook_url: 'https://hooks.slack.com/services/T/B/x' }),
      headers: { 'Content-Type': 'application/json' },
    })
    const res = await PATCH(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data.message).toBe('Slack webhook saved')
  })

  it('returns 422 when backend throws 422', async () => {
    vi.mocked(backendFetch).mockRejectedValueOnce(new Error('422'))
    const req = new Request('http://localhost/api/integrations/slack', {
      method: 'PATCH',
      body: JSON.stringify({ webhook_url: 'https://evil.com' }),
      headers: { 'Content-Type': 'application/json' },
    })
    const res = await PATCH(req)
    expect(res.status).toBe(422)
  })
})
