# Technical Context — Authentication & Access

## Current architecture
- Auth is a homegrown email/password service with session cookies; there is no support for federated identity.
- User records are keyed by email; there is no concept of an external identity provider or org-level identity mapping.

## Technical debt & dependencies
- The auth service has no abstraction for pluggable identity providers; SSO would require a new OIDC/SAML integration layer.
- A third-party library or a managed identity provider would likely be needed for SAML, adding a vendor dependency.

## Delivery complexity
- Estimated one to two engineers for roughly one quarter for a first SAML/OIDC integration, with SCIM as a follow-up.
- Migration risk: existing accounts must be linkable to IdP identities without locking users out.
