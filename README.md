# Python Backup Script

Gera periodicamente o backup de um banco de dados no servidor de produção e envia o arquivo
para um servidor de backup via SSH/SCP e/ou para um bucket AWS S3 (variável `BACKUP_TARGETS=ssh|s3|ssh,s3`).

O arquivo local só é apagado depois de estar em **todos** os destinos configurados; se algum
destino falhar, ele fica em `SOURCE_PATH` e é reenviado na próxima execução.

Engines suportados (variável `DB_ENGINE`):

| Engine     | Ferramenta | Arquivo gerado                         |
|------------|------------|----------------------------------------|
| `postgres` | `pg_dump`  | `backup_YYYYmmdd_HHMMSS.sql[.gz]`      |
| `firebird` | `gbak -b`  | `backup_YYYYmmdd_HHMMSS.fbk[.gz]`      |

Com `COMPRESS_BACKUP=true` (padrão), o arquivo é comprimido com gzip antes do envio.

## Configuração

Copie `.env.example` para `.env` e preencha as variáveis. Quais blocos você precisa preencher
depende de duas escolhas:

- `DB_ENGINE` define **qual banco** é copiado: preencha só o bloco `PG_*` ou só o `FB_*`.
- `BACKUP_TARGETS` define **para onde** o backup vai: preencha o bloco `SSH_*` + `DEST_PATH` (ssh),
  o bloco `S3_*` / `AWS_*` (s3), ou os dois (`ssh,s3`).

### Variáveis

**Gerais** (sempre necessárias)

| Variável          | Obrigatória | Padrão          | Descrição |
|-------------------|-------------|-----------------|-----------|
| `ENVIRONMENT`     | sim         | —               | Use `prod` no servidor. Com `dev`, `SOURCE_PATH` e `LOGS_DIR` são ignorados (usa `/srv/test_app/backup` e `./logs`). |
| `SOURCE_PATH`     | sim         | —               | Diretório **local** onde o dump é gerado antes do envio. Precisa existir e ter permissão de escrita. Os arquivos são apagados daqui depois de enviados a todos os destinos. |
| `LOGS_DIR`        | recomendada | `<projeto>/logs`| Diretório dos logs (`backup_script_YYYY-MM-DD.log`). Defina sempre ao usar o binário. |
| `DB_ENGINE`       | não         | `postgres`      | `postgres` ou `firebird`. |
| `COMPRESS_BACKUP` | não         | `true`          | Comprime o dump com gzip (`.gz`). |
| `BACKUP_TARGETS`  | não         | `ssh`           | `ssh`, `s3` ou `ssh,s3`. |

**PostgreSQL** (`DB_ENGINE=postgres`)

| Variável      | Obrigatória | Padrão      | Descrição |
|---------------|-------------|-------------|-----------|
| `PG_HOST`     | não         | `localhost` | Host do banco. |
| `PG_PORT`     | não         | `5432`      | Porta do banco. |
| `PG_DB_NAME`  | sim         | —           | Nome do banco. |
| `PG_USER`     | sim         | —           | Usuário com permissão de leitura em todo o banco. |
| `PG_PASSWORD` | sim         | —           | Senha (passada ao `pg_dump` via `PGPASSWORD`). |

**Firebird** (`DB_ENGINE=firebird`)

| Variável       | Obrigatória | Padrão      | Descrição |
|----------------|-------------|-------------|-----------|
| `FB_HOST`      | não         | `localhost` | Host do banco. |
| `FB_PORT`      | não         | `3050`      | Porta do banco. |
| `FB_DATABASE`  | sim         | —           | Caminho completo do `.fdb` no servidor ou alias do `databases.conf`. |
| `FB_USER`      | não         | `SYSDBA`    | Usuário. |
| `FB_PASSWORD`  | sim         | —           | Senha. |
| `FB_GBAK_PATH` | não         | `gbak`      | Caminho do `gbak` (veja [Firebird: `gbak`](#firebird-gbak)). |

**SSH** (`BACKUP_TARGETS` contém `ssh`)

| Variável       | Obrigatória | Padrão | Descrição |
|----------------|-------------|--------|-----------|
| `SSH_SERVER`   | sim         | —      | Host do servidor de backup. |
| `SSH_PORT`     | não         | `22`   | Porta SSH. |
| `SSH_USER`     | sim         | —      | Usuário SSH. |
| `PUB_KEY_PATH` | sim         | —      | Caminho da chave **privada** SSH (ex.: `/home/backup/.ssh/id_ed25519`). A chave pública correspondente deve estar no `authorized_keys` do servidor de backup. |
| `DEST_PATH`    | sim         | —      | Diretório no servidor de backup. É criado se não existir. |
| `BACKUP_DAYS`  | não         | `7`    | Retenção no servidor de backup: arquivos mais antigos que N dias são apagados lá. |

> `SSH_PASSWORD` existe no `.env.example`, mas hoje a autenticação é feita só por chave.

**AWS S3** (`BACKUP_TARGETS` contém `s3`)

| Variável                | Obrigatória | Padrão      | Descrição |
|-------------------------|-------------|-------------|-----------|
| `S3_BUCKET`             | sim         | —           | Nome do bucket (sem `s3://`). |
| `S3_PREFIX`             | não         | vazio       | "Pasta" dentro do bucket (ex.: `backups/postgres`). |
| `AWS_REGION`            | não         | `us-east-1` | Região do bucket (ex.: `sa-east-1`). |
| `AWS_ACCESS_KEY_ID`     | sim         | —           | Access key do usuário IAM do script. |
| `AWS_SECRET_ACCESS_KEY` | sim         | —           | Secret key do usuário IAM do script. |
| `S3_STORAGE_CLASS`      | não         | `STANDARD`  | Classe de armazenamento (veja a nota em [AWS S3](#aws-s3)). |

No S3, `DEST_PATH`, `BACKUP_DAYS` e as variáveis `SSH_*` não são usadas e podem ficar vazias.
A retenção é feita pela lifecycle rule do bucket.

### Exemplo: PostgreSQL → S3

```bash
ENVIRONMENT="prod"
SOURCE_PATH="/var/backups/db"
LOGS_DIR="/var/log/backup_script"

DB_ENGINE="postgres"
COMPRESS_BACKUP="true"
BACKUP_TARGETS="s3"

PG_HOST="localhost"
PG_PORT="5432"
PG_DB_NAME="meu_banco"
PG_USER="backup_user"
PG_PASSWORD="********"

S3_BUCKET="minha-empresa-backups"
S3_PREFIX="backups/postgres"
S3_STORAGE_CLASS="STANDARD"
AWS_REGION="sa-east-1"
AWS_ACCESS_KEY_ID="AKIA..."
AWS_SECRET_ACCESS_KEY="********"
```

### Exemplo: Firebird → SSH + S3

```bash
ENVIRONMENT="prod"
SOURCE_PATH="/var/backups/db"
LOGS_DIR="/var/log/backup_script"

DB_ENGINE="firebird"
BACKUP_TARGETS="ssh,s3"

FB_DATABASE="/var/lib/firebird/data/database.fdb"
FB_USER="SYSDBA"
FB_PASSWORD="********"
FB_GBAK_PATH="gbak"

SSH_SERVER="backup.minhaempresa.com.br"
SSH_PORT="22"
SSH_USER="backup"
PUB_KEY_PATH="/home/backup/.ssh/id_ed25519"
DEST_PATH="/srv/backups/firebird"
BACKUP_DAYS="7"

S3_BUCKET="minha-empresa-backups"
S3_PREFIX="backups/firebird"
AWS_REGION="sa-east-1"
AWS_ACCESS_KEY_ID="AKIA..."
AWS_SECRET_ACCESS_KEY="********"
```

### Firebird: `gbak`

`FB_GBAK_PATH` aceita o caminho completo (`/opt/firebird/bin/gbak`) ou só `gbak`, se ele estiver no `PATH`.
Como a instalação oficial do Firebird coloca o binário em `/opt/firebird/bin`, fora do `PATH`, dá para
criar um symlink e manter o padrão `FB_GBAK_PATH="gbak"`:

```bash
sudo ln -s /opt/firebird/bin/gbak /usr/bin/gbak
```

O script roda `gbak -b -v -g <host>/<porta>:<banco> <arquivo.fbk>` (`-g` desativa o garbage collection durante
o backup, o que deixa o processo mais rápido). As credenciais vão pelas variáveis de ambiente `ISC_USER` e
`ISC_PASSWORD`, que o gbak lê sozinho, e não por argumentos, para a senha não aparecer no `ps`. Para testar
o mesmo comando à mão:

```bash
ISC_USER=SYSDBA ISC_PASSWORD=<senha> gbak -b -v -g localhost/3050:/caminho/banco.fdb teste.fbk
# ou, com as credenciais como switches:
gbak -b -v -g -user SYSDBA -password <senha> localhost/3050:/caminho/banco.fdb teste.fbk
```

`FB_DATABASE` deve ser o caminho completo do `.fdb` no servidor, ou um alias definido em `databases.conf`.

## AWS S3

O envio usa `boto3` (não precisa do AWS CLI instalado). Preencha o bloco `S3_*` / `AWS_*` do `.env`
e proteja o arquivo: `chmod 600 .env`.

Policy IAM mínima para o usuário do script (sem permissão de delete, o que protege os backups se a chave vazar):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::<bucket>/<prefix>/*"
    }
  ]
}
```

A retenção no S3 é feita pela lifecycle rule do bucket (o script não apaga nada no S3).
Exemplo com expiração em 7 dias (configure uma vez, com uma conta que tenha permissão no bucket):

```bash
aws s3api put-bucket-lifecycle-configuration --bucket <bucket> --lifecycle-configuration '{
  "Rules": [{
    "ID": "expire-backups",
    "Status": "Enabled",
    "Filter": {"Prefix": "<prefix>/"},
    "Expiration": {"Days": 7}
  }]
}'
```

> O padrão é `S3_STORAGE_CLASS=STANDARD`. `STANDARD_IA` é mais barato por GB, mas a AWS cobra no mínimo
> 30 dias por objeto mesmo que a lifecycle o expire antes; só compensa com retenção de 30 dias ou mais.

## Uso

Dependências gerenciadas com [uv](https://docs.astral.sh/uv/):

```bash
uv sync     # cria o .venv e instala as dependências (inclui o grupo dev)
```

```bash
uv run task run    # executa o backup
uv run task test   # roda os testes
uv run task build  # gera o binário dist/backup_v2
```

O processo termina com código `0` em caso de sucesso e `1` em caso de erro (detalhes em `LOGS_DIR`).

## Deploy

O script roda no **servidor do banco** (é lá que o `pg_dump`/`gbak` gera o arquivo) e é agendado pelo cron.

### 1. Pré-requisitos no servidor

- `pg_dump` (PostgreSQL) ou `gbak` (Firebird) instalado. No PostgreSQL, a versão do `pg_dump`
  precisa ser igual ou maior que a do servidor do banco.
- Diretórios de `SOURCE_PATH` e `LOGS_DIR` criados, com permissão de escrita para o usuário que vai rodar o script:

  ```bash
  sudo mkdir -p /var/backups/db /var/log/backup_script
  sudo chown <usuario> /var/backups/db /var/log/backup_script
  ```

- Target SSH: chave SSH do usuário cadastrada no `authorized_keys` do servidor de backup.
  Teste antes: `ssh -i <PUB_KEY_PATH> <SSH_USER>@<SSH_SERVER>`.
- Target S3: bucket criado, usuário IAM com a policy mínima e a lifecycle rule configurada (veja [AWS S3](#aws-s3)).

### 2. Instalar o script

**Opção A: binário (não precisa de Python no servidor)**

Gere o binário numa máquina com a mesma distribuição Linux do servidor (ou mais antiga, por causa da glibc):

```bash
uv sync
uv run task build                       # gera dist/backup_v2
scp dist/backup_v2 <usuario>@<servidor>:/opt/backup_script/
```

**Opção B: código-fonte com uv**

```bash
git clone <repo> /opt/backup_script
cd /opt/backup_script
uv sync --no-dev
```

### 3. Criar o `.env`

Crie o `.env` em `/opt/backup_script/` (veja [Variáveis](#variáveis) e os exemplos acima) e proteja o arquivo:

```bash
chmod 600 /opt/backup_script/.env
```

> O binário procura o `.env` no **diretório atual** (e nos diretórios acima dele), não ao lado do executável.
> Por isso o cron precisa fazer `cd` para a pasta do `.env` antes de rodar.

### 4. Testar manualmente

```bash
cd /opt/backup_script && ./backup_v2          # opção A
cd /opt/backup_script && uv run python app/main.py   # opção B
echo $?                                       # 0 = sucesso
tail -n 50 /var/log/backup_script/backup_script_$(date +%F).log
```

Confira se o arquivo chegou ao destino (`DEST_PATH` no servidor de backup e/ou `s3://<bucket>/<prefix>/`)
e se foi removido de `SOURCE_PATH`.

### 5. Agendar no cron

`crontab -e` com o mesmo usuário do teste. Exemplo, todo dia às 02:00:

```cron
0 2 * * * cd /opt/backup_script && ./backup_v2
```

Com a opção B, use o caminho absoluto do `uv` (o cron tem um `PATH` reduzido; veja com `which uv`):

```cron
0 2 * * * cd /opt/backup_script && /home/<usuario>/.local/bin/uv run python app/main.py
```

## Restauração

Para baixar um backup do S3: `aws s3 cp s3://<bucket>/<prefix>/backup_20260101_020000.fbk.gz .`

```bash
# Firebird
gunzip backup_20260101_020000.fbk.gz
gbak -c -v -user SYSDBA -password <senha> backup_20260101_020000.fbk /caminho/novo.fdb

# PostgreSQL
gunzip backup_20260101_020000.sql.gz
psql -h localhost -U <usuario> -d <banco> -f backup_20260101_020000.sql
```
