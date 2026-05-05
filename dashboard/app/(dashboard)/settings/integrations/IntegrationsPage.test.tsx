import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock next/navigation so useSearchParams doesn't throw.
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}))

// Mock heavy sub-components so this test focuses on the Slack form only.
vi.mock('@/components/integrations/InstallButton', () => ({
  InstallButton: () => <div data-testid="install-button-mock">install-button</div>,
}))
vi.mock('@/components/integrations/ScanTriggerForm', () => ({
  ScanTriggerForm: ({ installationId }: { installationId: number }) => (
    <div data-testid="scan-trigger-form-mock">scan-trigger-form:{installationId}</div>
  ),
}))

describe('Integrations Slack form', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('calls PATCH /api/integrations/slack on submit with webhook URL', async () => {
    // The page also fetches /api/github/installations — return empty list.
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/api/github/installations')) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        })
      }
      // Slack PATCH call
      return Promise.resolve({
        ok: true,
        json: async () => ({ message: 'Slack webhook saved' }),
      })
    })

    const { default: IntegrationsPage } = await import('./page')
    render(<IntegrationsPage />)

    // Fill in the Slack webhook URL input
    const input = screen.getByPlaceholderText(/hooks\.slack\.com/i)
    fireEvent.change(input, {
      target: { value: 'https://hooks.slack.com/services/T/B/test' },
    })

    // Submit the form
    const saveButton = screen.getByRole('button', { name: /save webhook url/i })
    fireEvent.click(saveButton)

    // Assert fetch was called with the correct arguments
    await waitFor(() => {
      const calls = vi.mocked(global.fetch).mock.calls
      const slackCall = calls.find(
        ([url]) => typeof url === 'string' && url === '/api/integrations/slack',
      )
      expect(slackCall).toBeDefined()
      expect(slackCall![1]).toMatchObject({
        method: 'PATCH',
        body: JSON.stringify({ webhook_url: 'https://hooks.slack.com/services/T/B/test' }),
      })
    })

    // Assert success state: button shows 'Saved!'
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /saved!/i })).toBeTruthy()
    })
  })

  it('shows error message on 422 response', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/api/github/installations')) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        })
      }
      // Slack PATCH — error path
      return Promise.resolve({
        ok: false,
        status: 422,
        json: async () => ({ error: 'request_failed' }),
      })
    })

    const { default: IntegrationsPage } = await import('./page')
    render(<IntegrationsPage />)

    const input = screen.getByPlaceholderText(/hooks\.slack\.com/i)
    fireEvent.change(input, { target: { value: 'https://evil.com/hook' } })

    const saveButton = screen.getByRole('button', { name: /save webhook url/i })
    fireEvent.click(saveButton)

    // Assert error message visible
    await waitFor(() => {
      expect(screen.getByTestId('slack-error')).toBeTruthy()
    })
  })
})
