# OAuth 2.0 Authorization Principles
**Purpose**: Core OAuth 2.0 architectural principles independent of technology
**Audience**: Architects, developers, security auditors
**Layer**: 00_ARCHITECTURE
**Related**: None (innermost layer - no external dependencies)

## Intent

This document establishes the foundational OAuth 2.0 authorization principles that govern how external applications (like voice assistants) securely access protected resources without sharing credentials. These principles apply universally regardless of implementation technology.

## Core Concepts

### The Authorization Problem

**Scenario**: A user wants a voice assistant to control their music library, but:
1. User should not give their password to the voice assistant
2. Voice assistant needs limited access to specific operations
3. User should be able to revoke access without changing their password
4. Access should be time-limited and renewable

**Solution**: OAuth 2.0 Authorization Code Grant with PKCE

### Fundamental Principles

#### 1. Separation of Authorization and Authentication

**Authentication**: Proving who you are (handled by resource owner)
**Authorization**: Granting limited access to someone else (handled by OAuth)

The authorization server never authenticates the client application. It only:
- Authenticates the resource owner (user)
- Records the user's consent to grant access
- Issues tokens representing that granted access

#### 2. Token-Based Access Control

Access is represented by opaque tokens, not credentials:
- **Authorization Code**: Short-lived proof of user consent (5 minutes)
- **Access Token**: Medium-lived permission to access resources (1 hour)
- **Refresh Token**: Long-lived ability to obtain new access tokens (90 days)

**Principle**: Each token type has a specific purpose and lifetime. Authorization codes are single-use. Access tokens expire. Refresh tokens enable renewal without re-authorization.

#### 3. Client Type Security Models

OAuth defines two client security models based on ability to protect secrets:

**Confidential Clients**:
- Run on secure servers under developer control
- Can safely store shared secrets
- Authenticate using client_id + client_secret
- Example: Backend web services

**Public Clients**:
- Run on user devices (phones, voice assistants, browsers)
- Cannot safely store secrets (users could extract them)
- Use cryptographic proof instead of shared secrets (PKCE)
- Example: Mobile apps, voice assistants, single-page applications

**Principle**: Security mechanism must match client deployment environment. Secrets work for servers, cryptographic proof works for user devices.

#### 4. PKCE: Cryptographic Security Without Shared Secrets

Proof Key for Code Exchange (PKCE) solves the "authorization code interception" attack for public clients:

**The Attack Scenario Without PKCE**:
1. Attacker intercepts authorization code during redirect
2. Attacker uses intercepted code to get tokens
3. Attacker now has access to user's resources

**PKCE Protection Mechanism**:
1. Client generates random `code_verifier` (high entropy)
2. Client computes `code_challenge = SHA256(code_verifier)`
3. Client sends code_challenge during authorization
4. Authorization server binds code_challenge to authorization code
5. Client sends original code_verifier during token exchange
6. Authorization server verifies: SHA256(code_verifier) == stored code_challenge
7. Only the original client possesses the code_verifier

**Principle**: Cryptographic binding proves that the token requester is the same entity that obtained the authorization code, without requiring a shared secret.

#### 5. Redirect URI Validation

The redirect URI serves as a security anchor:
- Client pre-registers allowed redirect URIs with authorization server
- Authorization server only redirects to pre-registered URIs
- Token endpoint validates redirect_uri matches the authorization request

**Principle**: Prevents authorization code theft by ensuring codes can only be delivered to legitimate client endpoints.

#### 6. State Parameter CSRF Protection

The state parameter prevents Cross-Site Request Forgery:
- Client generates random state value
- Client includes state in authorization request
- Authorization server echoes state in redirect
- Client validates returned state matches original

**Principle**: Cryptographic binding between authorization request and response prevents attackers from injecting malicious authorization codes.

#### 7. Scope-Based Access Control

Scopes define granular permissions:
- Each scope represents a specific capability
- Client requests specific scopes during authorization
- User consents to requested scopes
- Access token is bound to granted scopes
- Resource server enforces scope-based access

**Principle**: Least privilege - clients receive only the minimum permissions needed for their function.

#### 8. Time-Limited Access with Renewal

Token lifetimes create security boundaries:
- **Authorization codes**: Very short (5 minutes) - one-time use
- **Access tokens**: Short to medium (1 hour) - frequently refreshed
- **Refresh tokens**: Long (90 days) - enables renewal

**Principle**: Short access token lifetimes limit damage from token theft. Refresh tokens enable seamless renewal without re-authorization.

## Authorization Flow Principles

### The Authorization Code Grant Flow

This is the most secure OAuth flow, designed for scenarios where:
- User has a web browser or equivalent (for consent screen)
- Client needs ongoing access (refresh tokens)
- High security is required

**Flow Stages**:

1. **Authorization Request** (User-Driven)
   - Client redirects user to authorization server
   - User sees consent screen showing requested permissions
   - User approves or denies access

2. **Authorization Code Issuance** (User Consent Result)
   - Authorization server generates short-lived code
   - Code is bound to: client_id, redirect_uri, scope, code_challenge (if PKCE)
   - Code is delivered to client via redirect

3. **Token Exchange** (Client-Driven)
   - Client exchanges code for tokens at token endpoint
   - Client proves identity (via client_secret OR code_verifier)
   - Authorization server validates all bindings

4. **Resource Access** (Ongoing)
   - Client uses access token to make API requests
   - Resource server validates token and scope
   - Token eventually expires

5. **Token Refresh** (Maintenance)
   - Client uses refresh token to get new access token
   - No user interaction required
   - Refresh token can be revoked by user at any time

**Principle**: Separation of user-driven authorization from client-driven token management. User consents once, client maintains access through token lifecycle.

## Security Properties

### What OAuth Guarantees

1. **Credential Isolation**: Client never sees user's password
2. **Scope Limitation**: Client can only access explicitly granted permissions
3. **Revocability**: User can revoke access without changing password
4. **Time Limitation**: Access tokens expire, forcing periodic validation
5. **Cryptographic Binding**: PKCE prevents code interception attacks
6. **CSRF Protection**: State parameter prevents request forgery

### What OAuth Does NOT Guarantee

1. **User Authentication**: OAuth is authorization, not authentication
2. **Token Confidentiality**: Tokens must be protected by client
3. **Client Trustworthiness**: OAuth assumes user trusts the client
4. **API Security**: Resource servers must validate tokens properly
5. **Refresh Token Protection**: Long-lived tokens require secure storage

**Principle**: OAuth solves the authorization problem. Other security concerns (TLS, secure storage, API validation) require separate solutions.

## Architectural Constraints

### 1. Stateful Authorization Codes

Authorization codes must be stored server-side with metadata:
- client_id (which client requested this code)
- redirect_uri (where to deliver tokens)
- code_challenge (PKCE binding)
- scope (granted permissions)
- expiration (5-minute TTL)
- user_id (who granted access)

**Constraint**: Authorization server must maintain state between authorization and token endpoints.

### 2. Single-Use Authorization Codes

Each authorization code can be exchanged for tokens exactly once.

**Rationale**: Prevents replay attacks. If a code is used twice, it indicates either:
- Attacker intercepted and replayed the code
- Client implementation bug

**Response**: Revoke ALL tokens issued for that authorization code.

### 3. Redirect URI Exact Matching

redirect_uri in token request must exactly match the one from authorization request.

**Rationale**: Prevents authorization code theft by ensuring codes can only be used by the client that requested them.

**Constraint**: No substring matching, no pattern matching. Exact byte-for-byte equality.

### 4. Client Type Determines Authentication Method

**Confidential clients**: MUST authenticate with client_secret
**Public clients**: MUST use PKCE, MUST NOT use client_secret

**Rationale**: Requiring client_secret for public clients creates false security. The secret would be extractable by users, providing no actual protection.

### 5. Token Opacity

Tokens should be opaque to clients (random strings, not JWTs).

**Rationale**:
- Prevents clients from making assumptions about token structure
- Allows authorization server to change token format
- Enables token revocation without changing client code

**Exception**: Some implementations use JWTs for stateless validation, trading flexibility for scalability.

## Quality Attributes

### Security

- **Confidentiality**: Authorization codes and tokens transmitted over HTTPS only
- **Integrity**: PKCE and state parameters prevent tampering
- **Non-repudiation**: Authorization server logs all consent grants

### Usability

- **Single Sign-On**: User authorizes once, client maintains access via refresh tokens
- **Graceful Degradation**: Token expiration prompts renewal, not re-authorization
- **Clear Consent**: User sees exactly what permissions they're granting

### Performance

- **Minimal Round-Trips**: Three HTTP requests for full authorization flow
- **Cacheable Tokens**: Access tokens valid for 1 hour
- **Async Token Refresh**: Clients can refresh tokens in background

### Scalability

- **Stateless Access Validation**: Resource servers validate tokens without coordination
- **Horizontal Scaling**: Authorization server can be load-balanced
- **Token Revocation**: Centralized revocation list scales via caching

## Compliance Standards

This architecture adheres to:

- **RFC 6749**: OAuth 2.0 Authorization Framework (base specification)
- **RFC 7636**: Proof Key for Code Exchange (PKCE) for OAuth Public Clients
- **RFC 6750**: OAuth 2.0 Bearer Token Usage
- **OAuth 2.0 Security Best Current Practice** (draft-ietf-oauth-security-topics)

## Verification

To verify an OAuth implementation follows these principles:

### Authorization Endpoint Verification
- [ ] Validates response_type=code (only authorization code grant)
- [ ] Validates client_id against registered clients
- [ ] Validates redirect_uri against pre-registered URIs
- [ ] Accepts optional code_challenge and code_challenge_method (PKCE)
- [ ] Accepts optional state parameter (CSRF protection)
- [ ] Returns authorization code via redirect with state echoed

### Token Endpoint Verification
- [ ] Validates grant_type (authorization_code or refresh_token)
- [ ] For public clients: Validates code_verifier against code_challenge
- [ ] For confidential clients: Validates client_secret
- [ ] Validates authorization code exists and not expired
- [ ] Validates authorization code not previously used
- [ ] Validates redirect_uri matches authorization request
- [ ] Returns access_token, refresh_token, expires_in, scope

### Security Verification
- [ ] Authorization codes expire in ≤5 minutes
- [ ] Authorization codes are single-use (invalidated after exchange)
- [ ] Access tokens have finite lifetime (recommended 1 hour)
- [ ] PKCE code_verifier has ≥256 bits of entropy
- [ ] State parameter has ≥128 bits of entropy
- [ ] All endpoints require HTTPS in production

### Client Type Verification
- [ ] Public clients (voice assistants, mobile apps): Use PKCE, no client_secret
- [ ] Confidential clients (backend services): Use client_secret, optional PKCE

## Design Rationale

### Why Authorization Code Grant?

**Alternatives Considered**:
1. **Implicit Grant**: Deprecated due to token exposure in browser history
2. **Password Grant**: Requires client to handle user credentials (violates OAuth principle)
3. **Client Credentials Grant**: No user involvement (not applicable for user authorization)

**Authorization Code Grant Selected Because**:
- Separates user consent from token issuance
- Supports refresh tokens for long-lived access
- Compatible with PKCE for public clients
- Industry standard for high-security scenarios

### Why PKCE for Public Clients?

**Problem**: Mobile apps and voice assistants cannot protect client_secret

**Solution Evolution**:
1. OAuth 2.0 (2012): Suggested state parameter and redirect URI validation
2. Industry: Still vulnerable to authorization code interception
3. RFC 7636 (2015): Introduced PKCE - cryptographic binding without secrets
4. OAuth 2.0 Security BCP (2020): Recommends PKCE for ALL clients

**Result**: PKCE is now the recommended approach for public clients, providing security equivalent to confidential clients without requiring shared secrets.

## See Also

- **[01_USE_CASES/ALEXA_ACCOUNT_LINKING.md](../01_USE_CASES/ALEXA_ACCOUNT_LINKING.md)** - User workflows for account linking
- **[02_REFERENCE/OAUTH_CONSTANTS.md](../02_REFERENCE/OAUTH_CONSTANTS.md)** - Token lifetimes and format specifications
- **[03_INTERFACES/OAUTH_ENDPOINTS.md](../03_INTERFACES/OAUTH_ENDPOINTS.md)** - Endpoint contracts and specifications
