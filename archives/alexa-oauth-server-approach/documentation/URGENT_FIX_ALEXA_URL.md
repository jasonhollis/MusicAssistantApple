# URGENT FIX: Alexa Authorization URL Issue

**Issue**: Phone cannot access OAuth server at `haboxhill.tail1cba6.ts.net`

**Root Cause**: Alexa Skill is configured with Tailscale MagicDNS hostname instead of custom domain

## Current (Broken) Configuration

**Alexa Skill Account Linking Settings**:
- Authorization URI: `https://haboxhill.tail1cba6.ts.net/alexa/authorize`
- Token URI: `https://haboxhill.tail1cba6.ts.net/alexa/token`

**Why This Fails**:
- `haboxhill.tail1cba6.ts.net` is a Tailscale MagicDNS name
- Only resolves for devices on your Tailscale network
- Your phone is NOT on Tailscale network
- Therefore: DNS resolution fails ("Server can't be found")

## Correct Configuration

**Alexa Skill Account Linking Settings** (CHANGE TO):
- Authorization URI: `https://music.jasonhollis.com:8096/alexa/authorize`
- Token URI: `https://music.jasonhollis.com:8096/alexa/token`

**Why This Works**:
- `music.jasonhollis.com` is your custom domain
- DNS CNAME: `music.jasonhollis.com` → `haboxhill.tail1cba6.ts.net`
- Your phone CAN resolve custom domains via public DNS
- Browser follows CNAME chain to reach Tailscale endpoint
- Tailscale Funnel serves via public HTTPS (Let's Encrypt cert)

## Fix Procedure (5 minutes)

### Step 1: Verify DNS CNAME (30 seconds)

From your Mac terminal:
```bash
dig music.jasonhollis.com CNAME +short
```

**Expected output**:
```
haboxhill.tail1cba6.ts.net.
```

If not showing CNAME record, check your DNS provider (the CNAME was configured on 2025-10-25 per SESSION_LOG).

### Step 2: Update Alexa Skill Configuration (3 minutes)

1. Go to: https://developer.amazon.com/alexa/console/ask
2. Select "Music Assistant" skill
3. Navigate to "Account Linking" section
4. Update these fields:

**OLD**:
```
Authorization URI: https://haboxhill.tail1cba6.ts.net/alexa/authorize
Access Token URI: https://haboxhill.tail1cba6.ts.net/alexa/token
```

**NEW**:
```
Authorization URI: https://music.jasonhollis.com:8096/alexa/authorize
Access Token URI: https://music.jasonhollis.com:8096/alexa/token
```

5. Click "Save"
6. Wait for Amazon to update configuration (~30 seconds)

### Step 3: Verify Custom Domain Access (1 minute)

From your phone (disconnected from Tailscale):
```
1. Open Safari
2. Navigate to: https://music.jasonhollis.com:8096/health
3. Expected: JSON response {"status":"ok",...}
```

If you see valid response → Custom domain is working.
If you see error → DNS CNAME not propagated yet (wait 5 minutes, retry).

### Step 4: Test Account Linking (1 minute)

1. Open Alexa app on phone
2. Navigate to Music Assistant skill
3. Tap "SETTINGS" button
4. Expected: Safari opens to `https://music.jasonhollis.com:8096/alexa/authorize?...`
5. Expected: Music Assistant login page loads (not "server can't be found")

## Why This Solution Works

### DNS Resolution Chain
```
Phone → music.jasonhollis.com
  ↓ (DNS CNAME)
  haboxhill.tail1cba6.ts.net
  ↓ (Tailscale public DNS)
  100.x.x.x (Tailscale IP)
  ↓ (Tailscale Funnel)
  Port 8096 → OAuth Server
```

### Certificate Validation
- Custom domain CNAME → Tailscale MagicDNS
- Browser TLS connection uses final hostname: `haboxhill.tail1cba6.ts.net`
- Tailscale wildcard cert `*.tail1cba6.ts.net` matches
- Certificate validation succeeds
- Safari shows green padlock (valid HTTPS)

## Verification Checklist

After completing fix procedure, verify:

- [ ] DNS CNAME resolves correctly (`dig` shows CNAME record)
- [ ] Custom domain accessible from phone (`https://music.jasonhollis.com:8096/health` works)
- [ ] Alexa Skill Authorization URI updated in developer console
- [ ] Account linking redirects to custom domain (not Tailscale hostname)
- [ ] Music Assistant login page loads in Safari (not DNS error)
- [ ] OAuth flow completes (authorization code generated)
- [ ] Alexa app shows "Account Linked" status

## If Still Not Working

### Issue: DNS CNAME not resolving
**Symptom**: `dig music.jasonhollis.com CNAME` shows no CNAME record
**Solution**:
1. Check DNS provider (where is `jasonhollis.com` registered?)
2. Verify CNAME record exists: `music.jasonhollis.com` → `haboxhill.tail1cba6.ts.net`
3. Wait 5-15 minutes for DNS propagation
4. Test from external DNS: `dig @8.8.8.8 music.jasonhollis.com CNAME`

### Issue: Certificate error in browser
**Symptom**: Safari shows "Certificate is invalid"
**Solution**:
- Ensure URL uses HTTPS (not HTTP)
- Ensure port `:8096` is in URL
- Wait for browser to resolve CNAME chain
- Verify Tailscale Funnel is running: SSH to haboxhill → `tailscale funnel status`

### Issue: "Connection refused" or timeout
**Symptom**: DNS resolves but connection fails
**Solution**:
1. Verify OAuth server is running on haboxhill:
   ```bash
   ssh haboxhill.local
   curl http://localhost:8096/health
   ```
2. Verify Tailscale Funnel is active:
   ```bash
   tailscale funnel status
   # Should show: https://haboxhill.tail1cba6.ts.net:8096 (Funnel on)
   ```
3. Restart Funnel if needed:
   ```bash
   tailscale funnel 8096
   ```

## Expected Timeline

- **Immediate**: Update Alexa Skill configuration (3 min)
- **Within 5 min**: Account linking works from phone
- **Within 10 min**: Complete OAuth flow, account linked

## Status After Fix

Once fixed:
- ✅ Phone can access OAuth endpoints via custom domain
- ✅ Alexa backend can access OAuth endpoints via custom domain
- ✅ Account linking flow works end-to-end
- ✅ Phase 2 testing can proceed

## Documentation to Update After Fix

Once working, update these files:
1. `SESSION_LOG.md` - Document URL fix and successful account linking test
2. `docs/05_OPERATIONS/MUSIC_ASSISTANT_ALEXA_VIABLE_PATHS.md` - Note custom domain requirement
3. `docs/04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md` - Document correct public URL

## References

- Custom Domain Setup: `docs/05_OPERATIONS/MUSIC_ASSISTANT_ALEXA_VIABLE_PATHS.md` (Step 3)
- DNS CNAME Configuration: SESSION_LOG.md line 95-98 (configured 2025-10-25)
- OAuth Server Implementation: `docs/04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md`
- Tailscale Funnel Status: SESSION_LOG.md line 92 (Funnel working on 2025-10-25)
