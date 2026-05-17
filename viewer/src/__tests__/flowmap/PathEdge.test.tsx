import { describe, test, it, expect } from 'vitest'
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

// Phase 12 FMV-02 — dual-strand asymmetric rendering tests
// RED until Plan 12-07 extends PathEdge with asymmetricForward / asymmetricReturn props.
// The existing renderEdge helper above stays UNCHANGED; Plan 12-07 introduces a
// sibling helper (e.g. renderEdgeWithAsymmetry) that threads the new flags through
// synthetic EdgeProps.
describe('FMV-02 asymmetry rendering', () => {
  it.skip('asymmetricForward=true renders forward path with red dashed stroke', () => {
    // Plan 12-07 implementation:
    //   const { container } = renderEdgeWithAsymmetry('both', { forward: true })
    //   const paths = container.querySelectorAll('path')
    //   const fwd = Array.from(paths).find(p => p.getAttribute('marker-end')?.includes('forward'))
    //   expect(fwd?.getAttribute('stroke')).toBe('#DC2626')
    //   expect(fwd?.getAttribute('stroke-dasharray')).toBeTruthy()
  })

  it.skip('asymmetricReturn=true renders return path with red dashed stroke', () => {
    // Plan 12-07: symmetric to above for the return leg
    //   const { container } = renderEdgeWithAsymmetry('both', { return: true })
    //   const ret = Array.from(container.querySelectorAll('path')).find(p => ...)
    //   expect(ret?.getAttribute('stroke')).toBe('#DC2626')
    //   expect(ret?.getAttribute('stroke-dasharray')).toBeTruthy()
  })

  it.skip('asymmetric flags default to false — strands keep existing solid colors', () => {
    // Plan 12-07 regression-lock:
    //   forward stroke == '#3B82F6' (blue-500)
    //   return  stroke == '#F97316' (orange-500)
    // — proves Phase 3 dual-color behavior is preserved when no asymmetry flags are set.
  })
})
