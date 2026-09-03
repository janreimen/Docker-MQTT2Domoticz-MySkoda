# Security Policy

## Supported Versions

Security fixes are currently provided for the latest released version of the project.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |
| < 0.1.0 | No        |

## Reporting a Security Vulnerability

Please **do not publicly disclose security vulnerabilities before they have been investigated**.

If you discover a security issue, please report it privately to the repository maintainer through GitHub.

When reporting a vulnerability, please include:

* A description of the vulnerability.
* The affected version.
* Steps required to reproduce the issue.
* The potential security impact.
* Any relevant logs or screenshots, after removing credentials and personal information.
* A proposed mitigation, if known.

Please do not include:

* MyŠkoda passwords.
* Domoticz passwords.
* API tokens.
* SSH private keys.
* MQTT credentials.
* Vehicle security PINs.
* Complete VINs unless strictly necessary.
* GPS coordinates or other personal data.

## Credentials and Secrets

This project requires credentials to communicate with MyŠkoda and, optionally, Domoticz and MQTT.

Secrets must **never be committed to Git**.

The following files should remain local:

```text
.env
```

The repository provides:

```text
.env.example
```

as a configuration template.

Before committing changes, verify:

```bash
git status
```

and ensure that `.env` is not staged.

You can also verify that Git ignores it:

```bash
git check-ignore -v .env
```

## Vehicle Information

Vehicle configuration may contain personally identifiable or sensitive information.

In particular:

* VINs
* Vehicle names
* GPS positions
* Mileage
* Vehicle status
* Maintenance information

should be treated as private information.

Do not publish real vehicle data in:

* GitHub issues
* Pull requests
* Documentation
* Screenshots
* Debug logs
* Public repositories

Use placeholders such as:

```text
YOUR_VIN
example@example.com
192.0.2.10
```

when documenting configuration.

## Logging

Logs may contain information returned by the MyŠkoda service or Domoticz.

Before sharing logs publicly, inspect them for:

* Email addresses
* VINs
* GPS coordinates
* Authentication information
* Vehicle identifiers
* Security-related information

Do not enable unnecessarily verbose logging in a production environment if it could expose sensitive vehicle information.

## Docker Security

The container requires network access to communicate with MyŠkoda and Domoticz.

The recommended deployment uses:

```yaml
network_mode: host
```

because it simplifies communication with services running on the host.

This also means that the container shares the host network namespace. The Docker host should therefore be appropriately secured.

The container should not be run with unnecessary privileges.

Do not add:

```yaml
privileged: true
```

unless a future feature explicitly requires it.

## File Permissions

The `.env` file contains credentials and should have restrictive permissions where supported:

```bash
chmod 600 .env
```

The state directory should also be protected from unauthorized users if it contains vehicle-specific information.

## Git Security

Before every commit, check:

```bash
git status
git diff --cached
```

Never commit:

```text
.env
*.key
*.pem
id_rsa
id_ed25519
credentials.json
secrets.json
```

If a secret is accidentally committed, **removing the file in a later commit is not sufficient**. The secret should be considered compromised and replaced immediately.

For example, if a password has been committed:

1. Change/revoke the password or credential.
2. Remove the secret from the repository history.
3. Check whether the credential was exposed publicly.
4. Review relevant logs for unauthorized use.

## Dependency Security

The project depends on external Python packages, including the MyŠkoda library.

Dependencies should be kept up to date where practical.

Security-sensitive dependency updates should be tested before deployment.

## Responsible Disclosure

Please allow reasonable time for a vulnerability to be investigated and fixed before making details public.

Security reports will be reviewed and addressed according to their severity and practical impact.

## Scope

This security policy covers:

* The Docker application.
* Application source code.
* Docker configuration supplied by this repository.
* Credential handling implemented by the application.
* Communication between the application and supported services.

Security issues in external services such as:

* Škoda's infrastructure,
* MyŠkoda itself,
* Domoticz,
* Docker,
* MQTT brokers,
* Python dependencies

should generally be reported to their respective maintainers when the issue is outside this project's control.

## Disclaimer

This project is an independent community project and is not affiliated with or endorsed by Škoda Auto or Volkswagen Group.

