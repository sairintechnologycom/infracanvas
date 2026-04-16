import Hero from '../components/Hero'
import DemoVideo from '../components/DemoVideo'
import ValueProps from '../components/ValueProps'
import FoundingMember from '../components/FoundingMember'
import TypeformCTA from '../components/TypeformCTA'

const SPOTS_REMAINING = 50 // Update manually after each payment and redeploy

export default function Home() {
  return (
    <>
      <Hero spotsRemaining={SPOTS_REMAINING} />
      <DemoVideo embedUrl={process.env.NEXT_PUBLIC_DEMO_VIDEO_URL || ''} />
      <ValueProps />
      <FoundingMember spotsRemaining={SPOTS_REMAINING} />
      <TypeformCTA />
    </>
  )
}
