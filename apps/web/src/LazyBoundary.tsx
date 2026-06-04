import { Component, type ReactNode } from 'react'

type Props = { fallback: ReactNode; children: ReactNode }
type State = { failed: boolean }

// A code-split chunk can 404 right after a deploy (a still-open or service-worker-cached
// document references an asset hash the new build has replaced). Suspense only handles the
// pending state, NOT an import() rejection, so without a boundary that rejection throws to
// the React root and blanks the whole page. Here the lazy content is decorative + aria-hidden
// (the 3D pitch, the hero canvas), so a failure degrades to the SVG/null fallback and the
// real accessibility content stays up. Self-heals on the next load once the new SW activates.
export class LazyBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  render(): ReactNode {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}
