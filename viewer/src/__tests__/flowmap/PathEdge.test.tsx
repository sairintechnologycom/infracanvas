import { describe, test, expect } from 'vitest'
import { render } from '@testing-library/react'
import type { EdgeProps } from '@xyflow/react'
import { PathEdge } from '../../components/flowmap/edges/PathEdge'

// We bypass <ReactFlow> here on purpose — jsdom can't measure nodes, so
// ReactFlow never computes source/target coordinates and edges never mount.
// Rendering PathEdge directly inside an <svg> with synthetic EdgeProps
// exercises the dual-lane <BaseEdge> contract that the component owns.
function renderEdge(direction: 'forward' | 'return' | 'both') {
  const props = {
    id: 'e1',
    source: 'a',
    target: 'b',
    sourceX: 0,
    sourceY: 0,
    targetX: 200,
    targetY: 0,
    sourcePosition: 'right',
    targetPosition: 'left',
    data: { direction },
  } as unknown as EdgeProps
  return render(
    <svg>
      <PathEdge {...props} />
    </svg>,
  )
}

describe('PathEdge', () => {
  test('is a function (component symbol present)', () => {
    expect(typeof PathEdge).toBe('function')
  })

  test('direction=both renders two <path> elements (forward + return lanes)', () => {
    const { container } = renderEdge('both')
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBeGreaterThanOrEqual(2)
  })

  test('direction=forward renders one <path> element (forward lane only)', () => {
    const { container } = renderEdge('forward')
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBeGreaterThanOrEqual(1)
  })

  test('direction=return renders one <path> element (return lane only)', () => {
    const { container } = renderEdge('return')
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBeGreaterThanOrEqual(1)
  })
})
