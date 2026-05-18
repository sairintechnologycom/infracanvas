import { BaseEdge, getSmoothStepPath, type EdgeProps } from '@xyflow/react'

interface PathEdgeData {
  direction?: 'forward' | 'return' | 'both'
  pathId?: string
  /** Phase 12 FMV-02 — when true, render forward leg with red dashed stroke */
  asymmetricForward?: boolean
  /** Phase 12 FMV-02 — when true, render return leg with red dashed stroke */
  asymmetricReturn?: boolean
}

// Phase 12 FMV-02 — dashed-red asymmetric leg styling
const ASYMMETRIC_STROKE = '#DC2626' // tailwind red-600
const ASYMMETRIC_DASH = '4 3' // 4px dash, 3px gap

// Dual-lane path rendering per UI-SPEC PathEdge:
//   forward lane: stroke #3B82F6, translated -3px perpendicular, markerEnd
//   return  lane: stroke #F97316, translated +3px perpendicular, markerStart
// In 3a network_paths is empty, so this edge type renders cold but unit-tests
// against synthetic PathHop fixtures still exercise the two-BaseEdge contract.
// Phase 12 FMV-02 layers asymmetric-leg overrides on top: when
// asymmetricForward / asymmetricReturn flags are set on edge data, the matching
// strand renders with stroke #DC2626 (red-600) + a 4-on/3-off dash pattern.
export function PathEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, data } = props
  const [edgePath] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY })
  const edgeData = data as PathEdgeData | undefined
  const direction = edgeData?.direction ?? 'both'

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

  // Phase 12 FMV-02 — asymmetric-leg overrides. When both flags are falsy, the
  // effective styles are the existing Phase 3 dual-color styles unchanged.
  const fwdEffective = edgeData?.asymmetricForward
    ? { ...forwardStyle, stroke: ASYMMETRIC_STROKE, strokeDasharray: ASYMMETRIC_DASH }
    : forwardStyle
  const retEffective = edgeData?.asymmetricReturn
    ? { ...returnStyle, stroke: ASYMMETRIC_STROKE, strokeDasharray: ASYMMETRIC_DASH }
    : returnStyle

  const renderForward = direction === 'forward' || direction === 'both'
  const renderReturn = direction === 'return' || direction === 'both'

  return (
    <>
      {renderForward && (
        <BaseEdge
          id={`${props.id}-forward`}
          path={edgePath}
          style={fwdEffective}
          markerEnd="url(#path-arrow-forward)"
        />
      )}
      {renderReturn && (
        <BaseEdge
          id={`${props.id}-return`}
          path={edgePath}
          style={retEffective}
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
