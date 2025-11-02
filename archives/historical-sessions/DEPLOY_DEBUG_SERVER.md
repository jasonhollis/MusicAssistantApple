# Deploy Debug OAuth Server

## Purpose
This enhanced version has comprehensive error logging to diagnose the 502 Bad Gateway issue.

## Deployment Steps

### 1. Copy debug server to remote host
```bash
scp oauth_server_debug.py root@192.168.1.137:/opt/music-assistant-oauth/
```

### 2. SSH into the server
```bash
ssh root@192.168.1.137
```

### 3. Stop the current server
```bash
cd /opt/music-assistant-oauth
pkill -f oauth_server.py
sleep 2
```

### 4. Backup current server (optional but recommended)
```bash
cp oauth_server.py oauth_server.py.backup
```

### 5. Replace with debug version
```bash
cp oauth_server_debug.py oauth_server.py
```

### 6. Run in foreground to see real-time errors
```bash
python3 -u oauth_server.py
```

**Leave this running** and open a new terminal window for testing.

### 7. In a NEW terminal, test the endpoint
```bash
ssh root@192.168.1.137

# Test from localhost (inside the server)
curl -v -X POST http://localhost:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=test_code&client_id=test_client"

# If that works, test from external URL
curl -v -X POST https://dev.jasonhollis.com/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=test_code&client_id=test_client"
```

### 8. Watch the first terminal window
You will see:
- Detailed request logging
- Form data contents
- Exact error messages
- Full Python tracebacks

This will show us EXACTLY what's breaking!

## What to Look For

### Success Pattern
```
=== INCOMING REQUEST ===
Method: POST
URL: http://localhost:8096/alexa/token
Form data: {'grant_type': 'authorization_code', ...}
=== TOKEN ENDPOINT START ===
Processing authorization_code grant
=== TOKEN ENDPOINT SUCCESS ===
Response status: 200
```

### Failure Pattern (will show one of these)
```
=== UNHANDLED EXCEPTION ===
Exception type: KeyError
Exception message: 'client_secret'
Traceback: ...
```

Or:
```
=== UNHANDLED ERROR IN TOKEN ENDPOINT ===
Exception type: AttributeError
Exception message: 'NoneType' object has no attribute ...
```

Or:
```
Exception type: ImportError
Exception message: No module named ...
```

## Expected Outcome

One of these will happen:

1. **Request succeeds** → Original code issue is fixed, just needs systemd restart
2. **ImportError** → Missing dependency (will see module name)
3. **KeyError/AttributeError** → Bug in request handling logic (will see exact line)
4. **No request arrives** → Reverse proxy misconfiguration (nginx issue)
5. **Connection refused** → Port binding issue (will see startup error)

## After Identifying the Issue

Once you know the exact error:

1. **Stop the foreground server** (Ctrl+C)
2. **Fix the actual oauth_server.py** based on the error
3. **Redeploy** with systemd:
   ```bash
   systemctl daemon-reload
   systemctl restart music-assistant-oauth
   systemctl status music-assistant-oauth
   ```

## Check Debug Logs Later

If you need to review what happened:
```bash
tail -100 /var/log/music-assistant-oauth-debug.log
```

## Restore Original Server (if needed)

If you want to go back to the previous version:
```bash
cd /opt/music-assistant-oauth
cp oauth_server.py.backup oauth_server.py
systemctl restart music-assistant-oauth
```

## Network Connectivity Issues?

If you can't reach the server at 192.168.1.137:

1. **Check if server is online**:
   ```bash
   ping 192.168.1.137
   ```

2. **Check if SSH is responding**:
   ```bash
   nc -zv 192.168.1.137 22
   ```

3. **Try alternate hostname**:
   ```bash
   ping littleubu.lan
   ssh root@littleubu.lan
   ```

4. **Check local network**:
   ```bash
   ifconfig | grep "inet "
   netstat -rn | grep default
   ```

---

## Summary

This debug server will show you **exactly** where the crash is happening. The enhanced logging captures:

- Every incoming request
- All form data
- Every step of token processing
- Full Python tracebacks for ANY error
- Response status codes

**No more guessing** - you'll see the actual error!
