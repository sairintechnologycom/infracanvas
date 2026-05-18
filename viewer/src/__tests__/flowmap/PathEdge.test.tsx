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
// Plan 12-07 extends PathEdge with asymmetricForward / asymmetricReturn props.
// The existing renderEdge helper above stays UNCHANGED; this block introduces a
// sibling helper (renderEdgeWithAsymmetry) that threads the new flags through
// synthetic EdgeProps.
function renderEdgeWithAsymmetry(
  direction: 'forward' | 'return' | 'both',
  asymmetric: { forward?: boolean; return?: boolean } = {},
) {
  const props = {
    id: 'e1',
    source: 's',
    target: 't',
    sourceX: 0,
    sourceY: 0,
    targetX: 100,
    targetY: 0,
    sourcePosition: 'right',
    targetPosition: 'left',
    data: {
      direction,
      asymmetricForward: asymmetric.forward,
      asymmetricReturn: asymmetric.return,
    },
  } as unknown as EdgeProps
  return render(
    <svg>
      <PathEdge {...props} />
    </svg>,
  )
}

// CSS rgb form of the tokens — jsdom normalises hex stroke values written
// via React's style prop to rgb() in the inline style attribute.
const RGB_DC2626 = 'rgb(220, 38, 38)' // tailwind red-600 — asymmetric
const RGB_3B82F6 = 'rgb(59, 130, 246)' // tailwind blue-500 — forward
const RGB_F97316 = 'rgb(249, 115, 22)' // tailwind orange-500 — return

describe('FMV-02 asymmetry rendering', () => {
  it('asymmetricForward=true renders forward path with red dashed stroke', () => {
    const { container } = renderEdgeWithAsymmetry('both', { forward: true })
    // Forward lane has BaseEdge id ending in -forward (visible) + a sibling
    // interaction path with no id; we target the visible one.
    const fwd = container.querySelector<SVGPathElement>('path[id$="-forward"]')
    expect(fwd).toBeTruthy()
    const style = fwd?.getAttribute('style') || ''
    expect(style).toContain(`stroke: ${RGB_DC2626}`)
    expect(style).toContain('stroke-dasharray:')
  })

  it('asymmetricReturn=true renders return path with red dashed stroke', () => {
    const { container } = renderEdgeWithAsymmetry('both', { return: true })
    const ret = container.querySelector<SVGPathElement>('path[id$="-return"]')
    expect(ret).toBeTruthy()
    const style = ret?.getAttribute('style') || ''
    expect(style).toContain(`stroke: ${RGB_DC2626}`)
    expect(style).toContain('stroke-dasharray:')
  })

  it('asymmetric flags default to false — strands keep existing solid colors', () => {
    const { container } = renderEdgeWithAsymmetry('both')
    const fwd = container.querySelector<SVGPathElement>('path[id$="-forward"]')
    const ret = container.querySelector<SVGPathElement>('path[id$="-return"]')
    const fwdStyle = fwd?.getAttribute('style') || ''
    const retStyle = ret?.getAttribute('style') || ''
    expect(fwdStyle).toContain(`stroke: ${RGB_3B82F6}`) // Phase 3 forward color preserved
    expect(retStyle).toContain(`stroke: ${RGB_F97316}`) // Phase 3 return color preserved
    // Regression: no dasharray when flags are falsy.
    expect(fwdStyle).not.toContain('stroke-dasharray:')
    expect(retStyle).not.toContain('stroke-dasharray:')
  })
})
