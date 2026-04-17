import type { Provider } from '../../lib/providerTheme';
import { PROVIDER_THEMES } from '../../lib/providerTheme';
import { getAwsIcon } from '../../icons/awsIconMap';
import { getAzureIcon } from '../../icons/azureIconMap';
import { ResourceIcon } from './ResourceIcon';

interface Props {
  provider: Provider;
  type: string;
  size?: number;
}

export function ServiceIcon({ provider, type, size = 48 }: Props) {
  const kind = PROVIDER_THEMES[provider].iconKind;

  if (kind === 'aws') {
    const Icon = getAwsIcon(type);
    // aws-react-icons uses `size` prop for dimensions; also pass width/height for SVGProps compat
    if (Icon) return <Icon size={size} width={size} height={size} />;
  } else if (kind === 'azure') {
    const Icon = getAzureIcon(type);
    if (Icon) return <Icon width={size} height={size} />;
  }

  return <ResourceIcon resourceType={type} size={size} />;
}
