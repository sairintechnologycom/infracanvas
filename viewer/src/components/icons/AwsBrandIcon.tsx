import { getAwsIcon } from '../../icons/awsIconMap'

interface Props {
  type: string
  size?: number
}

export function AwsBrandIcon({ type, size = 48 }: Props) {
  const Icon = getAwsIcon(type)
  if (!Icon) return null
  return <Icon width={size} height={size} />
}
