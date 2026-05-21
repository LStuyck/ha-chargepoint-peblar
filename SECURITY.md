# Security policy

## Reporting a vulnerability

If you find a security issue in this integration, **please do not file a public issue**. Instead:

- Use GitHub's [private security advisory](https://github.com/LStuyck/ha-chargepoint-peblar/security/advisories/new) feature, or
- Email the maintainer directly via the address on the GitHub profile.

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce it, ideally with a minimal example
- The integration version, Home Assistant version, and charger firmware version
- Whether you would like to be credited in the security advisory

The maintainer will acknowledge receipt within a few days and work on a fix as quickly as possible.

## Supported versions

This integration is community-maintained as a hobby project. Only the latest release receives security fixes. There is no backporting commitment for older releases.

## Scope

This integration runs entirely on the local network and never sends data to a third party. The API token is stored in Home Assistant's config-entry storage (encrypted at rest if your HA install uses encryption) and is redacted in the diagnostics download. If you find a path where the token, charger serial, or network state could leak unexpectedly, that's in scope.
