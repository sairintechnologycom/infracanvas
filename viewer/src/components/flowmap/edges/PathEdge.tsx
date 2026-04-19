import { BaseEdge, getSmoothStepPath, type EdgeProps } from '@xyflow/react'

interface PathEdgeData {
  direction?: 'forward' | 'return' | 'both'
  pathId?: string
}

// Dual-lane path rendering per UI-SPEC PathEdge:
//   forward lane: stroke #3B82F6, translated -3px perpendicular, markerEnd
//   return  lane: stroke #F97316, translated +3px perpendicular, markerStart
// In 3a network_paths is empty, so this edge type renders cold but unit-tests
// against synthetic PathHop fixtures still exercise the two-BaseEdge contract.
export function PathEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, data } = props
  const [edgePath] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY })
  const direction = (data as PathEdgeData | undefined)?.direction ?? 'both'

  const forwardStyle = {
    stroke: '#3B82F6',
    strokeWidth: 1.75,
    fill: 'none',
    transform: 'translate(0, -3px)',
  } as const
  const returnStyle = {
    stroke: '#F97316',
    strokeWidth: 1.75,
    fill: 'none',
    transform: 'translate(0, 3px)',
  } as const

  const renderForward = direction === 'forward' || direction === 'both'
  const renderReturn = direction === 'return' || direction === 'both'

  return (
    <>
      {renderForward && (
        <BaseEdge
          id={`${props.id}-forward`}
          path={edgePath}
          style={forwardStyle}
          markerEnd="url(#path-arrow-forward)"
        />
      )}
      {renderReturn && (
        <BaseEdge
          id={`${props.id}-return`}
          path={edgePath}
          style={returnStyle}
          markerStart="url(#path-arrow-return)"
        />
      )}
    </>
  )
}

// SVG marker definitions — injected once by FlowMapCanvas inside a hidden <svg>.
// All marker paths are pure JSX <path> elements; React auto-escapes attribute
// values, so no raw-HTML injection vector exists in this module (T-03-07-01).
export const pathEdgeMarkerDefs = (
  <defs>
    <marker id="path-arrow-forward" markerWidth={10} markerHeight={10} refX={8} refY={5} orient="auto">
      <path d="M0,0 L0,10 L8,5 z" fill="#3B82F6" />
    </marker>
    <marker
      id="path-arrow-return"
      markerWidth={10}
      markerHeight={10}
      refX={2}
      refY={5}
      orient="auto-start-reverse"
    >
      <path d="M0,5 L8,0 L8,10 z" fill="#F97316" />
    </marker>
  </defs>
)

export default PathEdge
