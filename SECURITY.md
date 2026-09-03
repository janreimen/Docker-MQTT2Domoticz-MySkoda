# Security Policy

## Docker-MQTT2Domoticz-MySkoda

This document describes the security considerations for the project.

**Current release: 0.1.1**

---

# Supported Versions

| Version | Supported   |
| ------- | ----------- |
| 0.1.1   | Yes         |
| 0.1.x   | Best effort |
| < 0.1.0 | No          |

Security fixes are primarily developed against the latest release.

---

# Reporting a Security Vulnerability

Please report security vulnerabilities privately rather than publishing them immediately in a public GitHub issue.

A security report should contain:

* A description of the vulnerability.
* The affected version.
* Steps to reproduce the issue.
* Potential security impact.
* Relevant logs, after removing sensitive information.
* A suggested mitigation, if available.

Do **not** include secrets in a security report.

In particular, never send:

* MyŠkoda passwords.
* Domoticz passwords.
* MQTT credentials.
* API tokens.
* SSH private keys.
* Vehicle security PINs.
* Unnecessary VINs.
* GPS coordinates.
* Personal account information.

---

# Credentials

The application uses credentials to communicate with external services.

Typical credentials include:

```text
SKODA_USERNAME
SKODA_PASSWORD
SKODA_SPIN
DOMOTICZ_USER
DOMOTICZ_PASSWORD
```

These values belong in:

```text
.env
```

and must never be committed to Git.

The repository provides:

```text
.env.example
```

as a template.

---

# Protect `.env`

The `.env` file contains sensitive credentials.

On Linux:

```bash
chmod 600 .env
```

Verify that Git ignores it:

```bash
git check-ignore -v .env
```

Before committing:

```bash
git status
```

Confirm that `.env` does not appear in the staged files.

---

# Git security

Before every commit:

```bash
git status
git diff --cached
```

Do not commit files containing:

```text
.env
*.key
*.pem
id_rsa
id_ed25519
credentials.json
secrets.json
```

If a credential is accidentally committed, deleting the file in a later commit does **not** make the credential safe.

Immediately:

1. Revoke or change the credential.
2. Remove the secret from Git history.
3. Check whether the repository was publicly accessible.
4. Review relevant service logs where possible.

---

# Vehicle information

The application handles vehicle-related information that should be considered private.

Potentially sensitive information includes:

* VINs.
* Vehicle names.
* Mileage.
* Driving range.
* Vehicle status.
* Maintenance information.
* Lock status.
* GPS position.
* Vehicle commands.

Do not publish real vehicle information in public:

* GitHub issues.
* Pull requests.
* Documentation.
* Screenshots.
* Debug logs.

Use placeholders such as:

```text
YOUR_VIN
YOUR_VEHICLE
example@example.com
```

when documenting the project.

---

# GPS information

GPS data is particularly sensitive.

If GPS functionality is not required, disable it:

```dotenv
GPS_ENABLED=false
```

Avoid publishing logs containing vehicle positions.

---

# Vehicle commands

The application can expose commands such as:

* Lock.
* Unlock.
* Wakeup.
* Honk / flash.
* Start/stop climatisation.
* Window heating.

These commands can cause real-world actions.

Access to the Domoticz interface should therefore be appropriately protected.

Do not expose the Domoticz API or this bridge directly to the public Internet without suitable authentication and network security controls.

---

# Domoticz permissions

Version 0.1.1 introduces automatic device provisioning.

The bridge may therefore perform Domoticz operations including:

* Reading hardware.
* Reading devices.
* Creating Dummy hardware.
* Creating virtual devices.
* Configuring devices.
* Updating devices.

The Domoticz account used by the application should have only the permissions necessary for these operations.

Where practical, use a **dedicated Domoticz account** for the bridge.

Do not use a full administrator account unless required by the Domoticz installation.

---

# Automatic provisioning

Automatic provisioning increases the privileges required by the Domoticz account compared with a read/update-only integration.

The provisioning functionality should therefore be disabled when it is not required:

```dotenv
DOMOTICZ_PROVISION=false
```

When provisioning is enabled, review the Domoticz account permissions carefully.

---

# Device state

The application stores Domoticz IDX mappings in:

```text
state/devices.json
```

This file can contain the relationship between:

```text
vehicle → Domoticz device → IDX
```

It should therefore be treated as application state and protected from unauthorized modification.

The file does not replace the need to protect the actual Domoticz installation.

Back it up together with the application configuration.

---

# Docker security

The recommended deployment uses:

```yaml
network_mode: host
```

This allows the container to communicate directly with services on the host network.

Host networking also means the container shares the host's network namespace.

The Docker host should therefore be appropriately secured.

The container should not be granted unnecessary privileges.

Do not add:

```yaml
privileged: true
```

unless a future feature explicitly requires it.

Do not mount sensitive host directories into the container.

---

# Network exposure

The bridge requires outbound network connectivity to MyŠkoda.

It also requires connectivity to Domoticz.

If MQTT is enabled, it requires connectivity to the configured MQTT broker.

Where possible:

* Restrict access to Domoticz.
* Restrict MQTT access.
* Do not expose the application directly to the Internet.
* Use firewall rules appropriate to the deployment.
* Use HTTPS where the environment requires encrypted Domoticz communication.

---

# Logging

Logs can contain information returned by external services.

Before sharing logs publicly, inspect them for:

* Email addresses.
* VINs.
* GPS coordinates.
* Vehicle identifiers.
* Credentials.
* Authentication information.
* API responses containing personal data.

Do not publish unrestricted debug logs containing private vehicle information.

---

# Backups

Backups may contain:

```text
.env
config/vehicles.csv
state/devices.json
```

Treat backups as sensitive data.

Store them securely and restrict access to authorized users.

In particular, `.env` backups contain authentication credentials.

---

# Dependencies

The application depends on external Python packages and services.

Dependencies should be reviewed and updated regularly.

Security updates should be tested before deployment.

The MyŠkoda integration relies on an unofficial interface/library and therefore depends on the continued availability and behavior of external Škoda services.

---

# Secret handling during development

Developers should use test credentials and placeholder vehicle information whenever possible.

Never use production credentials in:

* Source code.
* Unit tests.
* Documentation.
* Example configuration files.
* Git commit messages.
* Public issue reports.

The `.env.example` file must contain placeholders only.

---

# SSH keys

GitHub SSH authentication is recommended for repository access.

Only the **public** SSH key may be shared with GitHub.

Never commit or publish:

```text
~/.ssh/id_ed25519
~/.ssh/id_rsa
```

or any other private SSH key.

If a private key is exposed, treat it as compromised and replace it.

---

# Incident response

If credentials or other sensitive information are exposed:

1. Stop using the exposed credential.
2. Change or revoke it immediately.
3. Determine where the information was exposed.
4. Remove the information from repository history if applicable.
5. Review logs for unauthorized access.
6. Generate replacement credentials.
7. Update the deployment securely.

---

# Responsible disclosure

Security vulnerabilities should be reported privately.

Please provide reasonable time for investigation and remediation before public disclosure.

---

# Scope

This security policy covers:

* The Docker application.
* Application source code.
* Docker configuration supplied by this repository.
* Credential handling implemented by the application.
* Domoticz API integration.
* Automatic Domoticz provisioning.
* Application state handling.

Issues in third-party infrastructure should normally be reported to the relevant provider.

This includes:

* Škoda/MyŠkoda services.
* Domoticz.
* Docker.
* MQTT brokers.
* Python dependencies.
* Hosting or network infrastructure.

---

# Disclaimer

This is an independent community project.

It is not affiliated with, sponsored by, or endorsed by Škoda Auto or Volkswagen Group.

The application depends on external services that may change without notice.

