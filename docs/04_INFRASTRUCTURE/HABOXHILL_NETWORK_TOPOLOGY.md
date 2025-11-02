# HABoxHill Network Topology
**Purpose**: Document the actual container network architecture for Music Assistant OAuth infrastructure
**Audience**: System administrators, DevOps, network engineers
**Layer**: 04_INFRASTRUCTURE
**Related**: [ALEXA_OAUTH_ENDPOINTS_CONTRACT](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md), [HOME_ASSISTANT_CONTAINER_TOPOLOGY](../02_REFERENCE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md)

## Intent

This document maps the actual deployed infrastructure on the HABoxHill Home Assistant instance, specifically documenting how Music Assistant and Tailscale run as separate containers and how they communicate. This information is critical for configuring the OAuth server to be publicly accessible via Tailscale Funnel.

## Critical Discovery

**Initial Assumption**: Tailscale CLI would be available in the same container as Music Assistant
**Actual Reality**: Tailscale runs as a separate Home Assistant add-on container with its own network namespace

This architectural separation has significant implications for exposing the OAuth server (port 8096) publicly.

## Container Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ HABoxHill (Home Assistant Host)                                     │
│ IP: 100.126.41.17 (Tailscale)                                      │
│ IP: 192.168.7.15 (Local Network)                                   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Home Assistant Core Container                              │   │
│  │ - Main HA services                                         │   │
│  │ - Add-on management                                        │   │
│  │ - Configuration UI (port 8123)                            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Music Assistant Container                                  │   │
│  │ Container: music-assistant                                 │   │
│  │ Network: bridge mode (Docker)                              │   │
│  │                                                             │   │
│  │  Services:                                                  │   │
│  │  ├─ Music Assistant Server (port 8095)                    │   │
│  │  ├─ Web UI (served from 8095)                             │   │
│  │  └─ OAuth Server (port 8096) ⚠️ LOCAL ONLY                │   │
│  │                                                             │   │
│  │  OAuth Endpoints:                                           │   │
│  │  ├─ http://localhost:8096/health                          │   │
│  │  ├─ http://localhost:8096/alexa/authorize                 │   │
│  │  └─ http://localhost:8096/alexa/token                     │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Tailscale Container                                        │   │
│  │ Container ID: addon_a0d7b954_tailscale                    │   │
│  │ Hostname: a0d7b954-tailscale                              │   │
│  │ Network: Host network mode                                 │   │
│  │                                                             │   │
│  │  Services:                                                  │   │
│  │  ├─ Tailscale daemon (tailscaled)                         │   │
│  │  ├─ Tailscale CLI (tailscale)                             │   │
│  │  └─ Tailscale Funnel capability ✅ AVAILABLE              │   │
│  │                                                             │   │
│  │  Capabilities:                                              │   │
│  │  ├─ Can expose ports publicly via Funnel                  │   │
│  │  ├─ Can reach Music Assistant container                   │   │
│  │  └─ Has access to host network                            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Docker Bridge Network                                      │   │
│  │ - Connects all HA add-on containers                        │   │
│  │ - Internal DNS resolution between containers               │   │
│  │ - Music Assistant reachable from Tailscale container       │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Container Network Details

### Music Assistant Container

**Container Name**: `music-assistant`
**Network Mode**: Bridge (Docker default)
**Exposed Ports**:
- `8095`: Music Assistant web UI and API
- `8096`: OAuth server (NEW, local only)

**Internal IP**: Assigned by Docker bridge network
**Accessibility**:
- ✅ Accessible from host: `http://localhost:8095`, `http://localhost:8096`
- ✅ Accessible from other containers: Via Docker internal DNS
- ❌ Accessible from internet: NO (not exposed)
- ✅ Accessible from Tailscale network: Via host IP routing

**DNS Resolution**:
- From other containers: `music-assistant:8095`, `music-assistant:8096`
- From host: `localhost:8095`, `localhost:8096`
- From Tailscale container: `music-assistant:8096` (via Docker DNS)

### Tailscale Container

**Container ID**: `addon_a0d7b954_tailscale`
**Hostname**: `a0d7b954-tailscale`
**Network Mode**: Host (shares host network namespace)
**Special Capabilities**:
- Can bind to host ports
- Has full access to host network interfaces
- Can create Funnel tunnels

**Tailscale CLI Location**: `/usr/bin/tailscale` (inside container)
**Access Method**:
```bash
docker exec -it addon_a0d7b954_tailscale /bin/sh
```

**Funnel Capabilities**:
- Can expose any port on host network to public internet via HTTPS
- Handles TLS termination automatically
- Provides stable public URL: `https://a0d7b954-tailscale.ts.net`

### Home Assistant Core Container

**Purpose**: Main orchestrator and add-on manager
**Network**: Bridge mode with special privileges
**Accessibility**:
- Port 8123: Home Assistant web UI
- Manages all add-on containers
- Provides add-on configuration interface

## Network Communication Paths

### Path 1: Local Access (Within Host)

```
User's Browser → localhost:8096 → Docker Bridge → Music Assistant Container:8096
```

**Status**: ✅ WORKING
**Verification**:
```bash
curl http://localhost:8096/health
```

**Result**:
```json
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": [
    "/health",
    "/alexa/authorize",
    "/alexa/token"
  ]
}
```

### Path 2: Tailscale Network Access

```
Tailscale Client → Tailscale Network → HABoxHill:100.126.41.17:8096
                                     → Docker Bridge → Music Assistant:8096
```

**Status**: ⏸️ UNTESTED (but should work)
**Reason**: Port 8096 is exposed on host, Tailscale container has host network access

**Verification Command** (from another Tailscale device):
```bash
curl http://100.126.41.17:8096/health
```

### Path 3: Public Internet via Tailscale Funnel (TARGET)

```
Internet Client (Alexa) → HTTPS → Tailscale Funnel (TLS termination)
                                → Tailscale Container (reverse proxy)
                                → Docker Bridge
                                → Music Assistant Container:8096
```

**Status**: ⏸️ NOT CONFIGURED YET
**Required Configuration**: Tailscale Funnel setup with reverse proxy to Music Assistant

**Target URL**: `https://a0d7b954-tailscale.ts.net/alexa/*`

**How Funnel Works**:
1. Tailscale Funnel listens on public HTTPS port (443)
2. TLS termination handled by Tailscale infrastructure
3. Traffic proxied to local port (8096) in Tailscale container's network
4. Tailscale container forwards to Music Assistant via Docker bridge

### Path 4: Container-to-Container Communication

```
Tailscale Container → Docker DNS → music-assistant:8096
```

**Status**: ✅ VERIFIED WORKING
**Evidence**: User tested connectivity from Tailscale container

**Verification Command** (inside Tailscale container):
```bash
docker exec -it addon_a0d7b954_tailscale /bin/sh
wget -O- http://music-assistant:8096/health
```

## Port Mapping Table

| Service | Container | Internal Port | Host Port | Tailscale Funnel | Public URL |
|---------|-----------|---------------|-----------|------------------|------------|
| Music Assistant Web UI | music-assistant | 8095 | 8095 | No | - |
| OAuth Health Endpoint | music-assistant | 8096 | 8096 | **Needed** | `https://a0d7b954-tailscale.ts.net/health` |
| OAuth Authorize | music-assistant | 8096 | 8096 | **Needed** | `https://a0d7b954-tailscale.ts.net/alexa/authorize` |
| OAuth Token | music-assistant | 8096 | 8096 | **Needed** | `https://a0d7b954-tailscale.ts.net/alexa/token` |
| Home Assistant | homeassistant | 8123 | 8123 | No | - |
| Tailscale Admin | addon_a0d7b954_tailscale | - | - | N/A | - |

## IP Address Inventory

### HABoxHill Host

**Local Network IP**: `192.168.7.15`
- Accessible from local LAN
- Used for internal HA services

**Tailscale IP**: `100.126.41.17`
- Accessible from Tailscale network (Tailnet)
- Used for remote access to HA

**Tailscale Hostname**: `a0d7b954-tailscale`
**Tailscale FQDN**: `a0d7b954-tailscale.ts.net`
**Funnel-capable URL**: `https://a0d7b954-tailscale.ts.net`

### Container IPs

**Music Assistant**: Dynamic (Docker bridge assigns)
- Reachable via: `music-assistant` (Docker DNS)
- Reachable via: `localhost` (from host)

**Tailscale Container**: Uses host network (no separate IP)
- Shares all host IP addresses
- Can bind to any host port

## Network Security Boundaries

### Current Security Posture

**OAuth Server (Port 8096)**:
- 🔒 **Protected**: Not exposed to internet
- 🔒 **Protected**: Only accessible via Docker bridge network
- ✅ **Accessible**: From host (localhost)
- ✅ **Accessible**: From other containers (Docker DNS)
- ❌ **Not Accessible**: From internet (required for Alexa)

**Desired Security Posture** (After Tailscale Funnel):
- 🌐 **Public**: HTTPS endpoint via Tailscale Funnel
- 🔒 **Protected**: TLS encryption (Tailscale managed)
- 🔒 **Protected**: Tailscale ACLs (optional additional layer)
- ✅ **Accessible**: From Alexa servers (Amazon IP ranges)
- ✅ **Accessible**: From authorized OAuth clients

## Container Management Commands

### Accessing Containers

**Music Assistant Container**:
```bash
# Access shell (if bash available)
docker exec -it music-assistant /bin/bash

# Access shell (if only sh available)
docker exec -it music-assistant /bin/sh

# Check logs
docker logs music-assistant

# Check logs (follow mode)
docker logs -f music-assistant
```

**Tailscale Container**:
```bash
# Access shell
docker exec -it addon_a0d7b954_tailscale /bin/sh

# Run Tailscale command directly
docker exec addon_a0d7b954_tailscale tailscale status

# Check Funnel status
docker exec addon_a0d7b954_tailscale tailscale funnel status
```

**Home Assistant CLI** (from host):
```bash
# Access HA container
ha container restart music-assistant

# Check container status
ha container ls

# View container logs
ha container logs music-assistant
```

### Inspecting Network Configuration

**View Music Assistant Network Details**:
```bash
docker inspect music-assistant | grep -A 20 NetworkSettings
```

**View Tailscale Container Network Details**:
```bash
docker inspect addon_a0d7b954_tailscale | grep -A 20 NetworkSettings
```

**List All Container IPs**:
```bash
docker ps -q | xargs -n 1 docker inspect --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

## Implications for OAuth Setup

### Why Separate Containers Matter

**Challenge**: Cannot run Tailscale commands directly from Music Assistant container
- Music Assistant container has no Tailscale CLI installed
- Installing Tailscale in Music Assistant would violate container isolation
- Would require rebuilding Music Assistant container image

**Solution**: Use Tailscale container as reverse proxy
- Tailscale container already has Tailscale CLI
- Can configure Funnel to forward to Music Assistant
- Maintains clean separation of concerns

### OAuth Flow Through Containers

**Step 1: Alexa Authorization Request**
```
Alexa Service → HTTPS → https://a0d7b954-tailscale.ts.net/alexa/authorize?...
                      → Tailscale Funnel (TLS termination)
                      → Tailscale Container (reverse proxy)
                      → music-assistant:8096/alexa/authorize
                      → OAuth Server Response
```

**Step 2: User Authorization**
```
User Browser → Same path as Step 1
             → OAuth server presents authorization page
             → User approves/denies
```

**Step 3: Token Exchange**
```
Alexa Service → HTTPS → https://a0d7b954-tailscale.ts.net/alexa/token
                      → [Same reverse proxy path]
                      → music-assistant:8096/alexa/token
                      → OAuth Server Issues Token
```

**Critical Requirement**: Tailscale Funnel must forward ALL paths under `/alexa/*` to Music Assistant port 8096

## Architecture Comparison

### Before Understanding (Incorrect Assumption)

```
┌─────────────────────────────────┐
│ Music Assistant Container       │
│  ├─ Music Assistant Server      │
│  ├─ OAuth Server (port 8096)    │
│  └─ Tailscale CLI ❌ WRONG      │
│     (assumed to be here)         │
└─────────────────────────────────┘
```

**Implication**: Thought we could run `tailscale funnel` directly in Music Assistant container

### After Discovery (Correct Architecture)

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│ Music Assistant Container       │    │ Tailscale Container             │
│  ├─ Music Assistant Server      │←───│  ├─ Tailscale CLI ✅           │
│  ├─ OAuth Server (port 8096)    │    │  ├─ Tailscale Funnel           │
│  └─ No Tailscale ✅ CORRECT     │    │  └─ Reverse Proxy to MA:8096   │
└─────────────────────────────────┘    └─────────────────────────────────┘
          ↑                                         ↑
          └─────── Docker Bridge Network ───────────┘
```

**Implication**: Must configure Tailscale Funnel to forward traffic to Music Assistant

## Verification Procedures

### Verify Container Communication

**Test 1: Host can reach Music Assistant OAuth**
```bash
curl http://localhost:8096/health
# Expected: {"status":"ok", ...}
```

**Test 2: Tailscale container can reach Music Assistant**
```bash
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health
# Expected: {"status":"ok", ...}
```

**Test 3: Tailscale network can reach host OAuth** (from another Tailscale device)
```bash
curl http://100.126.41.17:8096/health
# Expected: {"status":"ok", ...}
```

**Test 4: Public internet can reach Funnel** (after configuration)
```bash
curl https://a0d7b954-tailscale.ts.net/health
# Expected: {"status":"ok", ...}
```

### Verify Network Isolation

**Test: Internet cannot directly access OAuth** (before Funnel)
```bash
# From external network (outside Tailscale)
curl http://192.168.7.15:8096/health
# Expected: Connection timeout or refused (firewall blocks it)
```

**Test: Containers are isolated**
```bash
# Try to access Tailscale container from Music Assistant
docker exec music-assistant ping a0d7b954-tailscale
# Expected: May or may not work (depends on Docker network config)
```

## Common Issues and Solutions

### Issue 1: "Tailscale CLI not found in Music Assistant container"

**Symptom**:
```bash
docker exec music-assistant tailscale status
# Error: executable file not found
```

**Root Cause**: Tailscale is in a separate container (`addon_a0d7b954_tailscale`)

**Solution**: Run commands in correct container:
```bash
docker exec addon_a0d7b954_tailscale tailscale status
```

### Issue 2: "Cannot reach OAuth server from Tailscale container"

**Symptom**:
```bash
docker exec addon_a0d7b954_tailscale wget http://music-assistant:8096/health
# Error: connection refused
```

**Root Cause**: OAuth server not running or Docker DNS not working

**Diagnosis**:
```bash
# 1. Check if OAuth server is running
curl http://localhost:8096/health  # From host

# 2. Check if Docker DNS works
docker exec addon_a0d7b954_tailscale nslookup music-assistant

# 3. Try host IP instead of DNS
docker exec addon_a0d7b954_tailscale wget http://172.17.0.1:8096/health
```

**Solution**:
- If OAuth not running: Check Music Assistant logs
- If DNS fails: Use host IP (`172.17.0.1` or `192.168.7.15`)
- If host IP fails: Check firewall rules

### Issue 3: "Funnel cannot forward to Music Assistant"

**Symptom**:
```bash
tailscale funnel on 8096
# Funnel listens on 443 but cannot reach Music Assistant
```

**Root Cause**: Funnel trying to reach `localhost:8096` in Tailscale container's network namespace, but Music Assistant is in different container

**Solution**: Configure Funnel to forward to Music Assistant container IP:
```bash
# Option 1: Use Docker DNS name
tailscale serve https / http://music-assistant:8096

# Option 2: Use container IP (find with docker inspect)
tailscale serve https / http://172.17.0.3:8096

# Option 3: Use host IP with port binding
tailscale serve https / http://192.168.7.15:8096
```

## Network Topology References

**Docker Bridge Network**:
- Default network for Home Assistant add-ons
- Provides automatic DNS resolution between containers
- Isolated from host network (except exposed ports)

**Tailscale Host Network Mode**:
- Tailscale container shares host's network namespace
- Can bind to any host port
- Has access to all host network interfaces
- Used for Funnel functionality

**Port Exposure**:
- Music Assistant exposes 8096 to host network
- Host port 8096 is accessible from Tailscale network
- Funnel can expose host ports to public internet

## See Also

- [TAILSCALE_OAUTH_ROUTING](../03_INTERFACES/TAILSCALE_OAUTH_ROUTING.md) - Network routing contract
- [HOME_ASSISTANT_CONTAINER_TOPOLOGY](../02_REFERENCE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md) - Container reference guide
- [TAILSCALE_FUNNEL_CONFIGURATION_HA](../05_OPERATIONS/TAILSCALE_FUNNEL_CONFIGURATION_HA.md) - Funnel setup procedures
- [ALEXA_OAUTH_ENDPOINTS_CONTRACT](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md) - OAuth API contract
- [ALEXA_OAUTH_SETUP_PROGRESS](../05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md) - Current implementation status
