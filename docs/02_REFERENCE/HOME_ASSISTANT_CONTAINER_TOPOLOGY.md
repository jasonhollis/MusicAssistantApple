# Home Assistant Container Topology Reference
**Purpose**: Quick reference guide for Home Assistant add-on containers and their network communication
**Audience**: System administrators, DevOps engineers, troubleshooters
**Layer**: 02_REFERENCE
**Related**: [HABOXHILL_NETWORK_TOPOLOGY](../04_INFRASTRUCTURE/HABOXHILL_NETWORK_TOPOLOGY.md), [TAILSCALE_OAUTH_ROUTING](../03_INTERFACES/TAILSCALE_OAUTH_ROUTING.md)

## Intent

This document serves as a quick reference for understanding how Home Assistant add-on containers are structured, how they communicate, and how to troubleshoot connectivity issues. Use this when you need fast answers about container networking, DNS resolution, or connectivity verification.

## Quick Reference Tables

### Container Inventory

| Container Name | Container ID | Network Mode | Purpose | Key Ports |
|----------------|--------------|--------------|---------|-----------|
| homeassistant | [varies] | Bridge | Home Assistant core | 8123 |
| music-assistant | [varies] | Bridge | Music Assistant server + OAuth | 8095, 8096 |
| addon_a0d7b954_tailscale | addon_a0d7b954_tailscale | Host | Tailscale VPN + Funnel | - |

### Port Mapping Quick Reference

| Service | Container Port | Host Port | Public Access | Notes |
|---------|---------------|-----------|---------------|-------|
| Home Assistant UI | 8123 | 8123 | Via Nabu Casa | Main HA interface |
| Music Assistant UI | 8095 | 8095 | Local only | Web interface |
| OAuth Server | 8096 | 8096 | **Need Funnel** | Alexa integration |
| Tailscale Admin | - | - | Via HA add-on UI | Configuration |

### Network Connectivity Matrix

| From Container | To Container | Method | Example |
|----------------|--------------|--------|---------|
| music-assistant | addon_a0d7b954_tailscale | Docker DNS | `tailscale:PORT` |
| addon_a0d7b954_tailscale | music-assistant | Docker DNS | `music-assistant:8096` ✅ |
| Host | music-assistant | localhost | `localhost:8095` ✅ |
| Host | addon_a0d7b954_tailscale | Docker exec | `docker exec ...` |
| Internet | music-assistant | **Not possible** | ❌ (need Funnel) |
| Internet | addon_a0d7b954_tailscale | Tailscale Funnel | `https://[hostname].ts.net` |

### DNS Resolution Quick Reference

| From Location | Target | Resolves To | Example |
|---------------|--------|-------------|---------|
| Inside music-assistant | tailscale | Tailscale container IP | `ping tailscale` |
| Inside addon_a0d7b954_tailscale | music-assistant | Music Assistant IP | `ping music-assistant` ✅ |
| Host | music-assistant | 127.0.0.1 (localhost) | `curl localhost:8095` ✅ |
| Host | addon_a0d7b954_tailscale | N/A (use docker exec) | `docker exec ...` |
| External | music-assistant | **Cannot resolve** | ❌ |
| External | a0d7b954-tailscale.ts.net | Tailscale public IP | ✅ |

## Container Types and Characteristics

### Bridge Network Containers

**Containers**: music-assistant, homeassistant (most HA add-ons)

**Characteristics**:
- Isolated network namespace (separate from host)
- Docker assigns internal IP address (172.17.0.X range typically)
- Port forwarding required for host access
- DNS resolution between containers (Docker internal DNS)
- Cannot directly bind to host ports

**Access Patterns**:
```bash
# From host
curl http://localhost:[HOST_PORT]

# From another container
curl http://[CONTAINER_NAME]:[CONTAINER_PORT]

# From internet
# ❌ Not possible without reverse proxy/Funnel
```

**Port Exposure**:
- Container port ≠ Host port (mapping required)
- Example: Container port 8095 → Host port 8095 (1:1 mapping)
- Configured in Home Assistant add-on configuration or Docker Compose

### Host Network Containers

**Containers**: addon_a0d7b954_tailscale

**Characteristics**:
- Shares host network namespace
- No network isolation from host
- Can bind to any host port directly
- Access to all host network interfaces
- No port forwarding needed

**Access Patterns**:
```bash
# From host
# Use host's IP address and port
curl http://localhost:[PORT]

# From another container
# Can reach via host IP or Docker DNS
curl http://addon_a0d7b954_tailscale:[PORT]

# From internet
# Can bind to public-facing ports (if configured)
```

**Why Tailscale Uses Host Mode**:
- Needs access to host network interfaces for VPN
- Must create virtual network interfaces (tailscale0)
- Requires low-level network privileges
- Funnel capability requires binding to host ports

## Container Communication Patterns

### Pattern 1: Container → Host

**Scenario**: Music Assistant needs to access host services

**Method**: Use special Docker DNS name `host.docker.internal` (on Mac/Windows) or host IP `172.17.0.1` (on Linux)

**Example**:
```bash
# From inside music-assistant container
curl http://host.docker.internal:8080    # Mac/Windows
curl http://172.17.0.1:8080              # Linux (HABoxHill)
```

**Common Uses**:
- Access host-level services (not in containers)
- Access system APIs
- Read host filesystem (if mounted)

### Pattern 2: Container → Container (Bridge Network)

**Scenario**: Tailscale container needs to access Music Assistant OAuth server

**Method**: Use Docker internal DNS with container name

**Example**:
```bash
# From inside addon_a0d7b954_tailscale container
curl http://music-assistant:8096/health  ✅ WORKING

# Alternative: Use container IP (less stable)
curl http://172.17.0.3:8096/health  # IP may change on restart
```

**DNS Resolution**:
- Docker automatically provides DNS resolution
- Container name → Container IP mapping
- Updated automatically when containers restart
- Faster and more reliable than IP addresses

**Verification**:
```bash
# Inside Tailscale container
nslookup music-assistant
# Output: IP address of music-assistant container

ping music-assistant
# Output: ICMP reply from music-assistant
```

### Pattern 3: Host → Container

**Scenario**: Host system needs to access containerized services

**Method**: Use `localhost` with mapped host port

**Example**:
```bash
# From HABoxHill host
curl http://localhost:8096/health  ✅ WORKING
curl http://localhost:8095          # Music Assistant UI
curl http://localhost:8123          # Home Assistant UI
```

**Port Mapping Requirement**:
- Container must expose port
- Port must be mapped to host
- Check with: `docker port [container_name]`

### Pattern 4: Container → Internet

**Scenario**: Music Assistant needs to fetch Apple Music API data

**Method**: Normal outbound connections (NAT handled by Docker)

**Example**:
```bash
# From inside music-assistant container
curl https://api.music.apple.com/...  ✅ Works automatically
```

**Characteristics**:
- Outbound connections allowed by default
- Docker NAT translates internal IP → Host IP
- Firewall rules typically allow outbound
- No special configuration needed

### Pattern 5: Internet → Container (Public Access)

**Scenario**: Alexa services need to access OAuth server

**Method**: Requires reverse proxy (Tailscale Funnel, Nabu Casa, nginx)

**Example**:
```
Internet → https://a0d7b954-tailscale.ts.net/alexa/authorize
        → Tailscale Funnel (TLS termination)
        → Tailscale container (reverse proxy)
        → music-assistant:8096/alexa/authorize  ✅ TARGET
```

**Why Direct Access Fails**:
- Container IPs are private (172.17.0.X)
- Not routable from internet
- Firewall blocks direct container access
- Security best practice (defense in depth)

**Solution Options**:
1. **Tailscale Funnel**: Public HTTPS via Tailscale network
2. **Nabu Casa Proxy**: nginx reverse proxy (if available)
3. **Port Forwarding + Dynamic DNS**: Insecure, not recommended

## How to Check Container Configuration

### List All Containers

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Filter by name
docker ps | grep music-assistant
```

**Expected Output**:
```
CONTAINER ID   IMAGE                        COMMAND   CREATED   STATUS   PORTS                    NAMES
abc123def456   music-assistant/latest       ...       2d ago    Up 2d    0.0.0.0:8095->8095/tcp   music-assistant
xyz789ghi012   tailscale/tailscale:latest   ...       5d ago    Up 5d                             addon_a0d7b954_tailscale
```

### Inspect Container Network Details

```bash
# Full network configuration
docker inspect music-assistant | grep -A 30 NetworkSettings

# Just the IP address
docker inspect music-assistant | grep IPAddress

# Network mode
docker inspect addon_a0d7b954_tailscale | grep NetworkMode
```

**Useful Fields**:
- `NetworkMode`: "bridge" or "host"
- `IPAddress`: Container's internal IP
- `Ports`: Port mappings (container → host)
- `Networks`: Which Docker networks container is connected to

### Check Port Mappings

```bash
# Show port mappings for specific container
docker port music-assistant

# Expected output:
8095/tcp -> 0.0.0.0:8095
8096/tcp -> 0.0.0.0:8096
```

**Interpretation**:
- `8095/tcp -> 0.0.0.0:8095`: Container port 8095 → Host port 8095
- `0.0.0.0` means listening on all interfaces
- If no output, container ports not exposed to host

### Verify Container Communication

```bash
# Test 1: Host → Music Assistant
curl http://localhost:8096/health
# Expected: {"status":"ok", ...}

# Test 2: Tailscale → Music Assistant (from inside Tailscale container)
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health
# Expected: {"status":"ok", ...}

# Test 3: Container DNS resolution
docker exec addon_a0d7b954_tailscale nslookup music-assistant
# Expected: IP address of music-assistant container

# Test 4: Container ping test
docker exec addon_a0d7b954_tailscale ping -c 3 music-assistant
# Expected: 3 successful ping replies
```

## Common Connectivity Issues

### Issue 1: "Cannot resolve container name"

**Symptom**:
```bash
docker exec addon_a0d7b954_tailscale ping music-assistant
# Error: bad address 'music-assistant'
```

**Diagnosis**:
```bash
# Check if container exists
docker ps | grep music-assistant

# Check if containers on same network
docker network inspect bridge | grep music-assistant
docker network inspect bridge | grep addon_a0d7b954_tailscale
```

**Solutions**:
1. Verify container is running: `docker ps`
2. Restart Docker daemon: `systemctl restart docker`
3. Use container IP instead: `docker inspect music-assistant | grep IPAddress`
4. Check if containers on different networks: `docker network ls`

### Issue 2: "Connection refused"

**Symptom**:
```bash
curl http://music-assistant:8096/health
# Error: Connection refused
```

**Diagnosis**:
```bash
# Check if OAuth server is running
curl http://localhost:8096/health  # From host

# Check Music Assistant logs
docker logs music-assistant | grep -i oauth

# Check if port is listening
docker exec music-assistant netstat -tlnp | grep 8096
```

**Solutions**:
1. Verify OAuth server is running (check logs)
2. Verify port 8096 is listening in container
3. Restart Music Assistant container
4. Check OAuth server configuration

### Issue 3: "No route to host"

**Symptom**:
```bash
curl http://172.17.0.3:8096/health
# Error: No route to host
```

**Diagnosis**:
```bash
# Check if container IP changed
docker inspect music-assistant | grep IPAddress

# Check firewall rules
iptables -L | grep 172.17
```

**Solutions**:
1. Use Docker DNS name instead of IP: `music-assistant:8096`
2. Check if container restarted (IP may have changed)
3. Verify Docker bridge network: `docker network inspect bridge`
4. Check iptables rules (may block container communication)

### Issue 4: "Connection timeout"

**Symptom**:
```bash
curl http://music-assistant:8096/health
# Hangs for 60+ seconds, then timeout
```

**Diagnosis**:
```bash
# Check if container is frozen
docker stats music-assistant

# Check container health
docker inspect music-assistant | grep Health

# Check system resources
free -h
df -h
```

**Solutions**:
1. Container may be overloaded (check CPU/memory usage)
2. Container may be frozen (restart it)
3. Host may be out of resources (check RAM/disk)
4. Network issue (check Docker daemon logs)

### Issue 5: "Public access fails (Funnel not working)"

**Symptom**:
```bash
# From internet
curl https://a0d7b954-tailscale.ts.net/health
# Error: 502 Bad Gateway or timeout
```

**Diagnosis**:
```bash
# Check Funnel status
docker exec addon_a0d7b954_tailscale tailscale funnel status

# Test Funnel → Music Assistant path
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health

# Check Tailscale logs
docker logs addon_a0d7b954_tailscale | tail -50
```

**Solutions**:
1. Verify Funnel is configured: `tailscale funnel status`
2. Verify Music Assistant is reachable from Tailscale container
3. Check Funnel routing configuration
4. Restart Tailscale Funnel: `tailscale funnel on 8096`
5. See detailed guide: [TAILSCALE_FUNNEL_CONFIGURATION_HA](../05_OPERATIONS/TAILSCALE_FUNNEL_CONFIGURATION_HA.md)

## Docker Network Commands Reference

### Inspect Docker Networks

```bash
# List all Docker networks
docker network ls

# Expected output:
NETWORK ID     NAME      DRIVER    SCOPE
abc123         bridge    bridge    local
def456         host      host      local
ghi789         none      null      local
```

**Network Types**:
- **bridge**: Default network for containers (isolated)
- **host**: Shares host network (no isolation)
- **none**: No network access

### Inspect Bridge Network

```bash
# Show all containers on bridge network
docker network inspect bridge

# Show just container names and IPs
docker network inspect bridge | grep -E "Name|IPv4Address"
```

**Expected Output**:
```json
{
  "Containers": {
    "abc123": {
      "Name": "music-assistant",
      "IPv4Address": "172.17.0.2/16"
    },
    "xyz789": {
      "Name": "homeassistant",
      "IPv4Address": "172.17.0.3/16"
    }
  }
}
```

### Test Network Connectivity

```bash
# Test connectivity between containers
docker exec addon_a0d7b954_tailscale ping -c 3 music-assistant

# Test DNS resolution
docker exec addon_a0d7b954_tailscale nslookup music-assistant

# Test specific port
docker exec addon_a0d7b954_tailscale nc -zv music-assistant 8096
# Expected: Connection to music-assistant 8096 port [tcp/*] succeeded!
```

### Troubleshoot Network Issues

```bash
# Restart Docker network
sudo systemctl restart docker

# Recreate bridge network (CAUTION: will restart containers)
docker network rm bridge
docker network create bridge

# Check Docker daemon logs
journalctl -u docker -n 50

# Check iptables rules (Docker creates these automatically)
sudo iptables -L -n | grep 172.17
```

## Home Assistant Add-on Specifics

### How HA Add-ons Differ from Regular Docker Containers

**Home Assistant Add-on Containers**:
- Managed by Home Assistant Supervisor
- Configuration via HA UI (Settings → Add-ons)
- Automatic restart on failure
- Integrated logs in HA UI
- Network isolation enforced by HA

**Regular Docker Containers**:
- Manually managed via `docker` command
- Configuration via Docker Compose or CLI flags
- Manual restart required
- Logs via `docker logs` command
- User controls network configuration

### Accessing HA Add-on Configuration

**Via Home Assistant UI**:
1. Go to Settings → Add-ons
2. Find add-on (e.g., Music Assistant)
3. Click "Configuration" tab
4. Modify settings (network, ports, options)
5. Click "Save" and restart add-on

**Via HA CLI** (on host):
```bash
# List add-ons
ha addons

# Get add-on info
ha addons info music-assistant

# Restart add-on
ha addons restart music-assistant

# View add-on logs
ha addons logs music-assistant
```

### HA Add-on Network Configuration

**Default Behavior**:
- All add-ons on same Docker bridge network
- Automatic DNS resolution between add-ons
- Port mapping configured in add-on config
- Firewall rules managed by HA Supervisor

**Custom Configuration**:
- Port mapping: Edit in add-on configuration
- Network mode: Some add-ons allow "host" mode
- Firewall: HA manages iptables rules automatically

**Example Add-on Network Config** (in HA UI):
```yaml
network:
  8095/tcp: 8095  # Music Assistant UI
  8096/tcp: 8096  # OAuth server
```

## Quick Diagnostic Commands

### One-Line Health Checks

```bash
# Check all containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check Music Assistant OAuth server
curl -f http://localhost:8096/health && echo "✅ OAuth server OK" || echo "❌ OAuth server FAILED"

# Check container connectivity
docker exec addon_a0d7b954_tailscale wget -q -O- http://music-assistant:8096/health && echo "✅ Container communication OK" || echo "❌ Container communication FAILED"

# Check public Funnel access (from external network)
curl -f https://a0d7b954-tailscale.ts.net/health && echo "✅ Public access OK" || echo "❌ Public access FAILED"
```

### Container Resource Usage

```bash
# Show CPU/memory usage
docker stats --no-stream music-assistant addon_a0d7b954_tailscale

# Check disk usage
docker system df

# Check container logs size
docker logs music-assistant 2>&1 | wc -l
```

### Network Troubleshooting Checklist

```bash
# 1. Container running?
docker ps | grep music-assistant

# 2. Port listening?
docker exec music-assistant netstat -tlnp | grep 8096

# 3. DNS resolution working?
docker exec addon_a0d7b954_tailscale nslookup music-assistant

# 4. Network connectivity?
docker exec addon_a0d7b954_tailscale ping -c 1 music-assistant

# 5. HTTP connectivity?
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health

# 6. Host access?
curl http://localhost:8096/health

# 7. Funnel configured?
docker exec addon_a0d7b954_tailscale tailscale funnel status
```

## See Also

- [HABOXHILL_NETWORK_TOPOLOGY](../04_INFRASTRUCTURE/HABOXHILL_NETWORK_TOPOLOGY.md) - Detailed infrastructure documentation
- [TAILSCALE_OAUTH_ROUTING](../03_INTERFACES/TAILSCALE_OAUTH_ROUTING.md) - Routing contract specification
- [TAILSCALE_FUNNEL_CONFIGURATION_HA](../05_OPERATIONS/TAILSCALE_FUNNEL_CONFIGURATION_HA.md) - Funnel setup guide
- [ALEXA_OAUTH_SETUP_PROGRESS](../05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md) - Current implementation status
