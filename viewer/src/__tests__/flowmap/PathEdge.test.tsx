import { describe, test, expect } from 'vitest'
import { render } from '@testing-library/react'
import { ReactFlow, ReactFlowProvider } from '@xyflow/react'
import { PathEdge } from '../../components/flowmap/edges/PathEdge'

function wrap(direction: 'forward' | 'return' | 'both') {
  return (
    <ReactFlowProvider>
      <div style={{ width: 400, height: 200 }}>
        <ReactFlow
          nodes={[
            { id: 'a', position: { x: 0, y: 0 }, data: {} },
            { id: 'b', position: { x: 200, y: 0 }, data: {} },
          ]}
          edges={[{ id: 'e1', source: 'a', target: 'b', type: 'path', data: { direction } }]}
          edgeTypes={{ path: PathEdge }}
          proOptions={{ hideAttribution: true }}
        />
      </div>
    </ReactFlowProvider>
  )
}

describe('PathEdge', () => {
  test('is a function (component symbol present)', () => {
    expect(typeof PathEdge).toBe('function')
  })

  test('direction=both renders at least two <path> elements', () => {
    const { container } = render(wrap('both'))
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBeGreaterThanOrEqual(2)
  })

  test('direction=forward renders at least one <path> element', () => {
    const { container } = render(wrap('forward'))
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBeGreaterThanOrEqual(1)
  })

  test('direction=return renders at least one <path> element', () => {
    const { container } = render(wrap('return'))
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBeGreaterThanOrEqual(1)
  })
})
