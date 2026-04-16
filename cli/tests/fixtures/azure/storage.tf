resource "azurerm_storage_account" "example" {
  name                     = "examplestorage"
  resource_group_name      = "example-resources"
  location                 = "East US"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  allow_blob_public_access = true
  min_tls_version          = "TLS1_0"
}

resource "azurerm_key_vault" "example" {
  name                = "example-vault"
  location            = "East US"
  resource_group_name = "example-resources"
  tenant_id           = "00000000-0000-0000-0000-000000000000"
  sku_name            = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
}
