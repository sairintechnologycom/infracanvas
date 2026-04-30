import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  TopBarActionsProvider,
  TopBarActionsSlot,
  useTopBarActions,
} from '@/components/layout/TopBarActions'

const TOPBAR = readFileSync(
  join(__dirname, '..', 'components', 'layout', 'TopBar.tsx'),
  'utf8',
)
const DASHLAYOUT = readFileSync(
  join(__dirname, '..', 'app', '(dashboard)', 'layout.tsx'),
  'utf8',
)

function Child({ tag }: { tag: string }) {
  const { set, clear } = useTopBarActions()
  return (
    <div>
      <button onClick={() => set(<span data-testid="injected">{tag}</span>)}>set</button>
      <button onClick={clear}>clear</button>
    </div>
  )
}

describe('TopBarActions slot pattern (RMD-05)', () => {
  it('Provider renders children unchanged', () => {
    render(
      <TopBarActionsProvider>
        <div data-testid="child" />
      </TopBarActionsProvider>,
    )
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('useTopBarActions throws outside provider', () => {
    // Suppress React's expected error log for the throw.
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Child tag="x" />)).toThrow(/TopBarActionsProvider/)
    errSpy.mockRestore()
  })

  it('set(jsx) injects into slot; clear() removes it', () => {
    render(
      <TopBarActionsProvider>
        <TopBarActionsSlot />
        <Child tag="hello" />
      </TopBarActionsProvider>,
    )
    act(() => {
      screen.getByText('set').click()
    })
    expect(screen.getByTestId('injected')).toHaveTextContent('hello')
    act(() => {
      screen.getByText('clear').click()
    })
    expect(screen.queryByTestId('injected')).toBeNull()
  })

  it('TopBar.tsx renders <TopBarActionsSlot/> on the right side', () => {
    expect(TOPBAR).toMatch(/TopBarActionsSlot/)
  })

  it('(dashboard)/layout.tsx wraps the shell in TopBarActionsProvider', () => {
    expect(DASHLAYOUT).toMatch(/TopBarActionsProvider/)
  })
})
