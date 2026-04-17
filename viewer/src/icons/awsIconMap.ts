import type { ComponentType, SVGProps } from 'react'
import {
  ArchitectureServiceAmazonSimpleStorageService,
  ArchitectureServiceAWSKeyManagementService,
  ArchitectureServiceAWSIdentityandAccessManagement,
  ArchitectureServiceAmazonEC2,
  ArchitectureServiceAWSLambda,
  ArchitectureServiceAmazonRDS,
  ArchitectureServiceAmazonDynamoDB,
  ArchitectureServiceAmazonVirtualPrivateCloud,
  ArchitectureServiceAmazonCloudFront,
  ArchitectureServiceAmazonCloudWatch,
  ArchitectureServiceAmazonRoute53,
  ArchitectureServiceAmazonSimpleNotificationService,
  ArchitectureServiceAmazonSimpleQueueService,
  ArchitectureServiceElasticLoadBalancing,
  ArchitectureServiceAWSSecretsManager,
  ArchitectureServiceAWSSystemsManager,
  ArchitectureServiceAWSWAF,
} from 'aws-react-icons'

type IconComponent = ComponentType<SVGProps<SVGSVGElement> & { size?: number }>

const MAP: Record<string, IconComponent> = {
  aws_s3_bucket:               ArchitectureServiceAmazonSimpleStorageService as IconComponent,
  aws_kms_key:                 ArchitectureServiceAWSKeyManagementService as IconComponent,
  aws_iam_role:                ArchitectureServiceAWSIdentityandAccessManagement as IconComponent,
  aws_iam_policy:              ArchitectureServiceAWSIdentityandAccessManagement as IconComponent,
  aws_iam_user:                ArchitectureServiceAWSIdentityandAccessManagement as IconComponent,
  aws_iam_group:               ArchitectureServiceAWSIdentityandAccessManagement as IconComponent,
  aws_iam_instance_profile:    ArchitectureServiceAWSIdentityandAccessManagement as IconComponent,
  aws_instance:                ArchitectureServiceAmazonEC2 as IconComponent,
  aws_lambda_function:         ArchitectureServiceAWSLambda as IconComponent,
  aws_db_instance:             ArchitectureServiceAmazonRDS as IconComponent,
  aws_rds_cluster:             ArchitectureServiceAmazonRDS as IconComponent,
  aws_dynamodb_table:          ArchitectureServiceAmazonDynamoDB as IconComponent,
  aws_vpc:                     ArchitectureServiceAmazonVirtualPrivateCloud as IconComponent,
  aws_cloudfront_distribution: ArchitectureServiceAmazonCloudFront as IconComponent,
  aws_cloudwatch_log_group:    ArchitectureServiceAmazonCloudWatch as IconComponent,
  aws_cloudwatch_metric_alarm: ArchitectureServiceAmazonCloudWatch as IconComponent,
  aws_route53_zone:            ArchitectureServiceAmazonRoute53 as IconComponent,
  aws_route53_record:          ArchitectureServiceAmazonRoute53 as IconComponent,
  aws_sns_topic:               ArchitectureServiceAmazonSimpleNotificationService as IconComponent,
  aws_sqs_queue:               ArchitectureServiceAmazonSimpleQueueService as IconComponent,
  aws_alb:                     ArchitectureServiceElasticLoadBalancing as IconComponent,
  aws_lb:                      ArchitectureServiceElasticLoadBalancing as IconComponent,
  aws_secretsmanager_secret:   ArchitectureServiceAWSSecretsManager as IconComponent,
  aws_ssm_parameter:           ArchitectureServiceAWSSystemsManager as IconComponent,
  aws_waf_web_acl:             ArchitectureServiceAWSWAF as IconComponent,
}

export function getAwsIcon(type: string): IconComponent | undefined {
  return MAP[type]
}
