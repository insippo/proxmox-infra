# VM.Monitor Permission Fix

## Probleem

Terraform provider nõuab `VM.Monitor` õigust, aga see ei ole Proxmox CLI-s kehtiv privilege nimi.

## Lahendus

`VM.Monitor` õigus tuleb lisada **Proxmox Web UI kaudu**, kuna see ei ole CLI kaudu seadistatav.

## Sammud

1. **Ava Proxmox Web UI:**
   - URL: `https://<PROXMOX_HOST>:8006` (asenda `<PROXMOX_HOST>` oma Proxmox serveri IP-ga)
   - Logi sisse

2. **Mine API Token'ite juurde:**
   - **Datacenter** → **Permissions** → **API Tokens**
   - Leia oma Terraform token (nt. `root@pam!terraform`)

3. **Lisa VM.Monitor õigus:**
   - Kliki token'i peale
   - **Permissions** sektsioonis:
     - **Path**: `/`
     - **Role**: ära vali **Administrator** — see annab kõik õigused kõigele.
       Selle repo token on juba korra ajalukku lekkinud, mistõttu ülelaia
       õigusega tokeni mõju on maksimaalne. Loo hoopis piiratud roll, mis
       sisaldab ainult Terraformile vajalikke privileege:

       ```bash
       pveum role add TerraformProv -privs \
         "VM.Allocate VM.Clone VM.Config.Disk VM.Config.Network \
          VM.Config.Options VM.Config.Cloudinit VM.Monitor VM.PowerMgmt \
          Datastore.Allocate Datastore.AllocateSpace Datastore.Audit"
       pveum acl modify / -token 'terraform@pam!terraform' -role TerraformProv
       ```

       Kui tokenil on `privsep=1`, tuleb õigused anda **tokenile endale**, mitte
       ainult omanik-kasutajale. Kontrolli skriptiga
       `scripts/check-proxmox-token-permissions.sh`.
   - Salvesta

4. **Testi:**
   ```bash
   cd terraform
   export TF_VAR_proxmox_api_token_id='<YOUR_TOKEN_ID>'
   export TF_VAR_proxmox_api_token_secret='<YOUR_TOKEN_SECRET>'
   export TF_VAR_proxmox_api_url='https://<PROXMOX_HOST>:8006/api2/json'
   export TF_VAR_proxmox_node='<PROXMOX_NODE>'
   terraform plan
   ```

## Märkused

- `VM.Monitor` ei ole Proxmox CLI-s (`pveum`) kehtiv privilege
- See on Proxmox 9.1 uus nõue või Terraform provider'i spetsiifiline nõue
- Administrator roll peaks sisaldama kõiki õigusi, sealhulgas VM.Monitor
- Kui probleem püsib, võib olla Terraform provider'i bug

## Alternatiivne lahendus

Kui Web UI kaudu ei saa, võib olla vaja:
- Uuendada Terraform provider'i uusimasse versiooni
- Või kasutada mõnda teist provider'i seadet

