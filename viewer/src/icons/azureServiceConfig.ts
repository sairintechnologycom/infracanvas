export interface AzureServiceConfig {
  color: string
  label: string
}

export const AZURE_SERVICE_CONFIG: Record<string, AzureServiceConfig> = {
  azurerm_virtual_network:         { color: '#0078D4', label: 'VNet' },
  azurerm_subnet:                  { color: '#0078D4', label: 'NET' },
  azurerm_network_security_group:  { color: '#DD344C', label: 'NSG' },
  azurerm_virtual_machine:         { color: '#FF9900', label: 'VM' },
  azurerm_linux_virtual_machine:   { color: '#FF9900', label: 'VM' },
  azurerm_windows_virtual_machine: { color: '#FF9900', label: 'VM' },
  azurerm_storage_account:         { color: '#3F8624', label: 'STG' },
  azurerm_kubernetes_cluster:      { color: '#2E73B8', label: 'AKS' },
  azurerm_app_service:             { color: '#FF9900', label: 'APP' },
  azurerm_mssql_server:            { color: '#2E73B8', label: 'SQL' },
  azurerm_key_vault:               { color: '#DD344C', label: 'KV' },
  azurerm_application_gateway:     { color: '#8C4FFF', label: 'AGW' },
}

export function getAzureServiceConfig(resourceType: string): AzureServiceConfig {
  if (AZURE_SERVICE_CONFIG[resourceType]) return AZURE_SERVICE_CONFIG[resourceType]
  return { color: '#94a3b8', label: resourceType.replace(/^azurerm_/, '').slice(0, 4).toUpperCase() }
}
