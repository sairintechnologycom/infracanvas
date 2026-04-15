import {
  ArchitectureServiceAmazonEC2,
  ArchitectureServiceAmazonSimpleStorageService,
  ArchitectureServiceAmazonRDS,
  ArchitectureServiceAWSLambda,
  ArchitectureServiceElasticLoadBalancing,
  ArchitectureServiceAmazonDynamoDB,
  ArchitectureServiceAWSKeyManagementService,
  ArchitectureServiceAWSIdentityandAccessManagement,
  ArchitectureServiceAmazonCloudFront,
  ArchitectureServiceAmazonSimpleQueueService,
  ArchitectureServiceAmazonSimpleNotificationService,
  ArchitectureServiceAmazonElastiCache,
  ArchitectureServiceAmazonElasticKubernetesService,
  ArchitectureServiceAmazonElasticContainerService,
  ArchitectureServiceAWSCloudTrail,
  ArchitectureServiceAmazonCloudWatch,
  ArchitectureServiceAWSSecretsManager,
  ArchitectureServiceAmazonAPIGateway,
} from 'aws-react-icons';

// Fallback generic cloud icon (simple SVG, no library dependency)
const GenericIcon = ({ size = 24 }: { size?: number | string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect x="2" y="6" width="20" height="12" rx="3" fill="#94a3b8" opacity="0.5"/>
    <rect x="6" y="10" width="12" height="4" rx="1" fill="#94a3b8"/>
  </svg>
);

const RESOURCE_ICON: Record<string, React.ComponentType<{ size?: number | string }>> = {
  'aws_instance':                          ArchitectureServiceAmazonEC2,
  'aws_vpc':                               GenericIcon,
  'aws_s3_bucket':                         ArchitectureServiceAmazonSimpleStorageService,
  'aws_db_instance':                       ArchitectureServiceAmazonRDS,
  'aws_rds_instance':                      ArchitectureServiceAmazonRDS,
  'aws_rds_cluster':                       ArchitectureServiceAmazonRDS,
  'aws_lambda_function':                   ArchitectureServiceAWSLambda,
  'aws_alb':                               ArchitectureServiceElasticLoadBalancing,
  'aws_lb':                                ArchitectureServiceElasticLoadBalancing,
  'aws_dynamodb_table':                    ArchitectureServiceAmazonDynamoDB,
  'aws_kms_key':                           ArchitectureServiceAWSKeyManagementService,
  'aws_iam_role':                          ArchitectureServiceAWSIdentityandAccessManagement,
  'aws_iam_policy':                        ArchitectureServiceAWSIdentityandAccessManagement,
  'aws_iam_instance_profile':              ArchitectureServiceAWSIdentityandAccessManagement,
  'aws_cloudfront_distribution':           ArchitectureServiceAmazonCloudFront,
  'aws_sqs_queue':                         ArchitectureServiceAmazonSimpleQueueService,
  'aws_sns_topic':                         ArchitectureServiceAmazonSimpleNotificationService,
  'aws_elasticache_cluster':               ArchitectureServiceAmazonElastiCache,
  'aws_elasticache_replication_group':     ArchitectureServiceAmazonElastiCache,
  'aws_eks_cluster':                       ArchitectureServiceAmazonElasticKubernetesService,
  'aws_ecs_service':                       ArchitectureServiceAmazonElasticContainerService,
  'aws_ecs_cluster':                       ArchitectureServiceAmazonElasticContainerService,
  'aws_cloudwatch_log_group':              ArchitectureServiceAmazonCloudWatch,
  'aws_cloudwatch_metric_alarm':           ArchitectureServiceAmazonCloudWatch,
  'aws_cloudtrail':                        ArchitectureServiceAWSCloudTrail,
  'aws_secretsmanager_secret':             ArchitectureServiceAWSSecretsManager,
  'aws_api_gateway_rest_api':              ArchitectureServiceAmazonAPIGateway,
  'aws_apigatewayv2_api':                  ArchitectureServiceAmazonAPIGateway,
};

interface AwsIconProps {
  resourceType: string;
  size?: number;
}

export function AwsIcon({ resourceType, size = 24 }: AwsIconProps) {
  const Icon = RESOURCE_ICON[resourceType] ?? GenericIcon;
  return <Icon size={size} />;
}
