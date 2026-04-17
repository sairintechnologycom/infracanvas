import type { ComponentType, SVGProps } from 'react';
import { AzureStorageAccount } from './azure/StorageAccount';
import { AzureVirtualMachine } from './azure/VirtualMachine';
import { AzureVirtualNetwork } from './azure/VirtualNetwork';
import { AzureSubnet } from './azure/Subnet';
import { AzureNetworkSecurityGroup } from './azure/NetworkSecurityGroup';
import { AzureKeyVault } from './azure/KeyVault';
import { AzureSqlDatabase } from './azure/SqlDatabase';
import { AzureCosmosDb } from './azure/CosmosDb';
import { AzureAppService } from './azure/AppService';
import { AzureFunctionApp } from './azure/FunctionApp';
import { AzureLoadBalancer } from './azure/LoadBalancer';
import { AzurePublicIp } from './azure/PublicIp';
import { AzureResourceGroup } from './azure/ResourceGroup';
import { AzureFirewall } from './azure/Firewall';

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

const MAP: Record<string, IconComponent> = {
  azurerm_storage_account: AzureStorageAccount,
  azurerm_virtual_machine: AzureVirtualMachine,
  azurerm_linux_virtual_machine: AzureVirtualMachine,
  azurerm_windows_virtual_machine: AzureVirtualMachine,
  azurerm_virtual_network: AzureVirtualNetwork,
  azurerm_subnet: AzureSubnet,
  azurerm_network_security_group: AzureNetworkSecurityGroup,
  azurerm_key_vault: AzureKeyVault,
  azurerm_sql_database: AzureSqlDatabase,
  azurerm_mssql_database: AzureSqlDatabase,
  azurerm_cosmosdb_account: AzureCosmosDb,
  azurerm_cosmosdb_sql_database: AzureCosmosDb,
  azurerm_app_service: AzureAppService,
  azurerm_linux_web_app: AzureAppService,
  azurerm_windows_web_app: AzureAppService,
  azurerm_function_app: AzureFunctionApp,
  azurerm_linux_function_app: AzureFunctionApp,
  azurerm_windows_function_app: AzureFunctionApp,
  azurerm_lb: AzureLoadBalancer,
  azurerm_public_ip: AzurePublicIp,
  azurerm_resource_group: AzureResourceGroup,
  azurerm_firewall: AzureFirewall,
};

export function getAzureIcon(type: string): IconComponent | undefined {
  return MAP[type];
}
