export interface AwsServiceConfig {
  color: string;
  label: string;
}

export const AWS_SERVICE_CONFIG: Record<string, AwsServiceConfig> = {
  aws_instance:                { color: '#FF9900', label: 'EC2' },
  aws_alb:                     { color: '#FF9900', label: 'ALB' },
  aws_lb:                      { color: '#FF9900', label: 'LB' },
  aws_nat_gateway:             { color: '#FF9900', label: 'NAT' },
  aws_eip:                     { color: '#FF9900', label: 'EIP' },
  aws_cloudfront_distribution: { color: '#FF9900', label: 'CDN' },
  aws_lambda_function:         { color: '#FF9900', label: 'λ' },
  aws_db_instance:             { color: '#2E73B8', label: 'RDS' },
  aws_rds_instance:            { color: '#2E73B8', label: 'RDS' },
  aws_dynamodb_table:          { color: '#2E73B8', label: 'DDB' },
  aws_s3_bucket:               { color: '#3F8624', label: 'S3' },
  aws_vpc:                     { color: '#8C4FFF', label: 'VPC' },
  aws_subnet:                  { color: '#8C4FFF', label: 'NET' },
  aws_internet_gateway:        { color: '#8C4FFF', label: 'IGW' },
  aws_security_group:          { color: '#DD344C', label: 'SG' },
  aws_kms_key:                 { color: '#DD344C', label: 'KMS' },
  aws_iam_role:                { color: '#DD344C', label: 'IAM' },
  aws_iam_policy:              { color: '#DD344C', label: 'IAM' },
  aws_sqs_queue:               { color: '#E7157B', label: 'SQS' },
  aws_sns_topic:               { color: '#E7157B', label: 'SNS' },
};

export function getServiceConfig(resourceType: string): AwsServiceConfig {
  if (AWS_SERVICE_CONFIG[resourceType]) return AWS_SERVICE_CONFIG[resourceType];
  // Prefix matching
  for (const [key, cfg] of Object.entries(AWS_SERVICE_CONFIG)) {
    const prefix = key.replace(/_[^_]+$/, '');
    if (resourceType.startsWith(prefix)) return cfg;
  }
  return { color: '#94a3b8', label: resourceType.replace(/^aws_/, '').slice(0, 4).toUpperCase() };
}
