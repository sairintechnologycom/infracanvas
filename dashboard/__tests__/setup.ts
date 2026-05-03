import '@testing-library/jest-dom'

// jsdom lacks ResizeObserver, which @xyflow/react and other libraries may need.
class ResizeObserverPolyfill {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = ResizeObserverPolyfill as unknown as typeof ResizeObserver
}

// Radix-UI primitives (Select, etc.) call hasPointerCapture on click targets;
// jsdom doesn't implement the Pointer Events spec. Stub the methods so
// tests can drive open/close on shadcn Select without TypeErrors.
type ElProto = Element & {
  hasPointerCapture?: (id: number) => boolean
  releasePointerCapture?: (id: number) => void
  setPointerCapture?: (id: number) => void
  scrollIntoView?: (arg?: boolean | ScrollIntoViewOptions) => void
}
const proto = Element.prototype as ElProto
if (typeof proto.hasPointerCapture !== 'function') {
  proto.hasPointerCapture = () => false
}
if (typeof proto.releasePointerCapture !== 'function') {
  proto.releasePointerCapture = () => {}
}
if (typeof proto.setPointerCapture !== 'function') {
  proto.setPointerCapture = () => {}
}
if (typeof proto.scrollIntoView !== 'function') {
  proto.scrollIntoView = () => {}
}
