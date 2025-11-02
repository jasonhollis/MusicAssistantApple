# Phase 2 Account Linking Validation Guide

## Quick Start

This guide provides real-time validation procedures for monitoring the OAuth server during account linking tests.

## Validation Workflow

### Before Testing (Pre-Flight Check)

**Run the pre-test health check to ensure everything is ready:**

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"
bash validation/phase2_pretest_check.sh
```

**This checks:**
- OAuth container is running
- Local server responding (http://localhost:8099)
- Tailscale Funnel is active
- Public HTTPS endpoint accessible
- SSL certificate valid
- OAuth endpoints ready

**Expected output:** All green checkmarks ✓

**If any checks fail:** Script will tell you exactly what to fix

---

### During Testing (Real-Time Monitoring)

**In a separate terminal window, start the log monitor:**

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"
bash validation/phase2_log_monitor.sh
```

**This displays:**
- Color-coded log events in real-time
- Authorization requests (green)
- Token requests (blue)
- Token generation (yellow)
- Redirects (magenta)
- Errors (red)

**Keep this running** while you perform account linking in the Alexa app.

**What to do:**
1. Open Alexa app on your phone
2. Go to: More > Skills & Games > Your Skills
3. Find "Music Assistant" skill
4. Tap "Link Account"
5. **Watch the logs** - you should see events appearing immediately

**Expected sequence (within 3-6 seconds):**
1. Green: Authorization request received
2. Yellow: Authorization code generated
3. Magenta: Redirecting to Alexa
4. Blue: Token exchange request
5. Yellow: Access token generated
6. Yellow: Refresh token generated

**If you see errors (red):** Keep the log monitor running and proceed to post-test validation

---

### After Testing (Validation)

**Stop the log monitor (Ctrl+C) and run post-test validation:**

```bash
bash validation/phase2_posttest_validation.sh
```

**This checks:**
- Were all OAuth flow steps completed?
- Were tokens generated?
- Were there any errors?
- Was token response sent to Alexa?

**Possible outcomes:**

1. **SUCCESS** (green) - All steps completed
   - Verify account shows as "Linked" in Alexa app
   - Test the skill: "Alexa, open Music Assistant"

2. **PARTIAL SUCCESS** (yellow) - Code generated but no tokens
   - Check Alexa app for error messages
   - Try account linking again
   - Verify Client Secret in Alexa Developer Console

3. **FAILED** (red) - Authorization endpoint never called
   - Re-run pre-test health check
   - Verify Authorization URI in Alexa Developer Console
   - Check Tailscale Funnel accessibility

---

### If Account Linking Failed (Diagnostics)

**Run the detailed diagnostics script:**

```bash
bash validation/phase2_diagnostics.sh
```

**This performs 8-step diagnostic:**
1. Was /authorize endpoint called? (Is Alexa reaching your server?)
2. Was authorization code generated? (Did validation pass?)
3. Was redirect sent to Alexa? (Did server respond correctly?)
4. Was token exchange requested? (Did Alexa complete the flow?)
5. Were client credentials validated? (Is Client Secret correct?)
6. Was authorization code validated? (Did code expire or mismatch?)
7. Were tokens generated? (Did token creation succeed?)
8. Was token response sent? (Did server respond to Alexa?)

**The script will identify exactly which step failed and suggest fixes.**

---

### Inspecting Generated Tokens

**To examine the tokens that were generated:**

```bash
bash validation/phase2_inspect_tokens.sh
```

**This shows:**
- Full access token and refresh token
- Token format (JWT vs opaque)
- JWT header and payload (if applicable)
- Token expiration times
- Security analysis (length, uniqueness)
- Usage examples (how to test with API)

**Use this to:**
- Verify tokens are correctly formatted
- Check expiration times
- Test tokens with Music Assistant API
- Debug token-related issues

---

## Expected Log Sequence

See detailed documentation: `validation/EXPECTED_LOG_SEQUENCE.md`

**Successful flow logs:**
```
[INFO] GET /authorize - Authorization request received
[INFO] Client ID validated: alexa-music-assistant
[INFO] Authorization code generated: abc123def456
[INFO] Redirecting to: https://pitangui.amazon.com/api/skill/link/...
[INFO] POST /token - Token exchange request received
[INFO] Client credentials validated: alexa-music-assistant
[INFO] Authorization code validated: abc123def456
[INFO] Access token generated: eyJhbGci...
[INFO] Refresh token generated: rt_abc123...
[INFO] Token response sent successfully
```

**Total duration:** 3-6 seconds from "Link Account" click to completion

---

## Common Error Patterns

### Error 1: "Authorization endpoint not called"

**Symptoms:**
- No logs appear when clicking "Link Account"
- Alexa app shows generic error

**Diagnosis:**
```bash
bash validation/phase2_diagnostics.sh
```

**Common causes:**
- Wrong Authorization URI in Alexa Developer Console
- Tailscale Funnel not running or blocked
- DNS resolution issue

**Fix:**
1. Check Authorization URI matches Funnel URL
2. Test Funnel URL in browser: `curl -I <funnel-url>/health`
3. Restart Funnel: `tailscale funnel --bg --https=443 8099`

---

### Error 2: "Authorization code generated but no tokens"

**Symptoms:**
- Logs show authorization code creation
- Logs show redirect sent
- No token exchange request appears

**Diagnosis:**
```bash
bash validation/phase2_posttest_validation.sh
```

**Common causes:**
- Alexa didn't complete redirect (user closed browser)
- Network timeout between Alexa and server
- Redirect URL malformed

**Fix:**
1. Check Alexa app for error messages
2. Try account linking again
3. Verify redirect URL in logs matches Alexa pattern

---

### Error 3: "Client authentication failed"

**Symptoms:**
- Token exchange request received
- Error: "Client authentication failed"
- HTTP 401 Unauthorized

**Diagnosis:**
```bash
docker logs oauth-server 2>&1 | grep -A 5 "POST /token"
```

**Common causes:**
- Wrong Client Secret in Alexa Developer Console
- Client Secret doesn't match OAuth server config

**Fix:**
1. Verify Client Secret in Alexa Developer Console
2. Ensure it matches OAuth server configuration
3. Restart OAuth server if secret was changed

---

### Error 4: "Invalid authorization code"

**Symptoms:**
- Token exchange request received
- Error: "Authorization code not found or expired"

**Common causes:**
- Code expired (>10 minutes since generation)
- Code already used (codes are single-use)
- Code mismatch

**Fix:**
1. Check time between code generation and token exchange
2. Ensure user didn't click "Link Account" multiple times
3. Try fresh account linking attempt

---

## Testing Checklist

**Before Account Linking:**
- [ ] OAuth container running (`docker ps | grep oauth-server`)
- [ ] Tailscale Funnel active (`tailscale funnel status`)
- [ ] Pre-test health check passes (all green ✓)
- [ ] Log monitor running in separate terminal

**During Account Linking:**
- [ ] Watch logs for authorization request (green)
- [ ] See authorization code generation (yellow)
- [ ] See redirect to Alexa (magenta)
- [ ] See token exchange request (blue)
- [ ] See token generation (yellow)
- [ ] No errors (red) appear

**After Account Linking:**
- [ ] Post-test validation shows success
- [ ] Alexa app shows account as "Linked"
- [ ] No errors in logs
- [ ] Tokens inspected and validated

**If Failed:**
- [ ] Run diagnostics script
- [ ] Identify which step failed
- [ ] Apply suggested fixes
- [ ] Re-run pre-test health check
- [ ] Try account linking again

---

## Quick Command Reference

```bash
# Health check before testing
bash validation/phase2_pretest_check.sh

# Monitor logs during testing (separate terminal)
bash validation/phase2_log_monitor.sh

# Validate after testing
bash validation/phase2_posttest_validation.sh

# Diagnose failures
bash validation/phase2_diagnostics.sh

# Inspect generated tokens
bash validation/phase2_inspect_tokens.sh

# View full logs
docker logs oauth-server

# View last 50 log lines
docker logs --tail 50 oauth-server

# Follow logs in real-time
docker logs -f oauth-server
```

---

## Alexa App Verification

**After successful account linking:**

1. **Open Alexa app**
2. **Navigate to:** More > Skills & Games > Your Skills
3. **Find:** "Music Assistant" skill
4. **Verify:** Shows "Linked" (not "Link Account")
5. **Test:** Say "Alexa, open Music Assistant"

**If still showing "Link Account" despite logs showing success:**
- Alexa may not have stored tokens (Alexa-side issue)
- Try disabling and re-enabling skill in developer console
- Clear Alexa app cache
- Wait 5-10 minutes (Alexa sync delay)

---

## Next Steps After Successful Linking

1. **Test basic skill invocation:**
   - Say: "Alexa, open Music Assistant"
   - Should respond with custom skill response (not account linking prompt)

2. **Test API requests with access token:**
   - Extract access token: `bash validation/phase2_inspect_tokens.sh`
   - Test with Music Assistant API (when implemented)

3. **Monitor token expiration:**
   - Access token expires in 1 hour
   - Test refresh token flow before expiration

4. **Move to Phase 3:**
   - Implement actual skill functionality
   - Handle user requests with access token
   - Call Music Assistant API

---

## Troubleshooting Resources

**Documentation:**
- Expected log sequence: `validation/EXPECTED_LOG_SEQUENCE.md`
- This guide: `validation/PHASE2_VALIDATION_GUIDE.md`

**Scripts:**
- All validation scripts: `validation/phase2_*.sh`
- Make executable: `chmod +x validation/phase2_*.sh`

**Logs:**
- OAuth server: `docker logs oauth-server`
- Tailscale Funnel: `tailscale funnel status`

**Support:**
- Alexa Developer Console: https://developer.amazon.com/alexa/console/ask
- OAuth 2.0 RFC: https://tools.ietf.org/html/rfc6749

---

## Security Notes

**Token Security:**
- Tokens shown in logs are for development/testing only
- In production, NEVER log tokens in plaintext
- Store tokens securely (encrypted database)
- Implement token rotation and revocation

**HTTPS Only:**
- Always use HTTPS for OAuth endpoints (Tailscale Funnel provides this)
- Never use HTTP for production OAuth flows
- Validate SSL certificates

**Client Secret:**
- Keep Client Secret confidential
- Don't commit to version control
- Rotate periodically in production

---

**Ready to test? Start with the pre-test health check!**

```bash
bash validation/phase2_pretest_check.sh
```
