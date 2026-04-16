resource "azurerm_kubernetes_cluster" "example" {
  name                = "example-aks"
  location            = "East US"
  resource_group_name = "example-resources"
  dns_prefix          = "exampleaks"
  kubernetes_version  = "1.24"
  role_based_access_control_enabled = false

  default_node_pool {
    name       = "default"
    node_count = 1
    vm_size    = "Standard_D2_v2"
  }
}

resource "azurerm_mssql_server" "example" {
  name                         = "example-sqlserver"
  resource_group_name          = "example-resources"
  location                     = "East US"
  version                      = "12.0"
  administrator_login          = "sqladmin"
  administrator_login_password = "P@ssw0rd123!"
  public_network_access_enabled = true
}
