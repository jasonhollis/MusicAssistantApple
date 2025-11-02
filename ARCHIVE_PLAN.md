# MusicAssistantApple Project Cleanup and Archive Plan

**Date**: 2025-11-02
**Purpose**: Reorganize project to reflect correct architecture (Alexa → HA → Music Assistant)
**Status**: READY TO EXECUTE

---

## Executive Summary

### What We Learned

After analyzing the deployed system on haboxhill.local, we discovered:

1. **✅ OAuth2 Already Working**: The `/config/custom_components/alexa/` integration (from alexa-oauth2 project) handles ALL OAuth2 authentication
2. **❌ OAuth Server Approach Wrong**: The `alexa_oauth_endpoints.py` file is architectural duplication
3. **✅ Music Assistant Deployed**: `/config/custom_components/music_assistant/` already exposes MA players to HA
4. **Missing Piece**: Smart home handler to route Alexa directives from HA to Music Assistant

### What This Cleanup Does

**Move to Archives**:
- Apple Music API integration work (different problem than we're solving)
- Obsolete Alexa OAuth server approach (duplicates alexa-oauth2)
- Historical documentation from exploration phase

**Keep Active**:
- `INTEGRATION_STRATEGY.md` - Correct architecture understanding
- `APPLY_ALEXA_OAUTH2_FIXES.md` - Security analysis (useful reference)
- Core project structure (README, PROJECT.md, DECISIONS.md, SESSION_LOG.md)

---

## File Categorization

### Category 1: Apple Music Integration Work (OBSOLETE)

**Why Obsolete**: These files solve Apple Music API integration, but we're actually building Alexa → HA → Music Assistant integration.

**Archive Location**: `archives/apple-music-integration/`

**Files to Move**:

**Documentation**:
- `00_START_HERE_PLAYLIST_FIX.md` - Apple Music playlist sync issue
- `PLAYLIST_FIX_README.md` - Apple Music playlists
- `PLAYLIST_FIX_STATUS.md` - Apple Music playlists
- `README_PLAYLIST_FIX.md` - Apple Music playlists
- `PLAYLIST_SYNC_ANALYSIS.md` - Apple Music playlists
- `UNICODE_FIX_INDEX.md` - Apple Music unicode issues
- `UNICODE_FIX_PATCH.md` - Apple Music unicode fixes
- `UNICODE_FIX_QUICK_REFERENCE.txt` - Apple Music unicode
- `UNICODE_FIX_README.md` - Apple Music unicode
- `UNICODE_FIX_SUMMARY.md` - Apple Music unicode
- `SPATIAL_AUDIO_EXPLANATION.md` - Apple Music spatial audio
- `SPATIAL_AUDIO_TRUTH.md` - Apple Music spatial audio
- `APPLY_STREAMING_PAGINATION_PATCH.md` - Apple Music streaming
- `PAGINATION_ISSUE_ANALYSIS.md` - Apple Music pagination
- `ALPHABETICAL_NAVIGATION_README.md` - Apple Music UI
- `ALPHABETICAL_NAVIGATION_SOLUTION.md` - Apple Music UI
- `APPLE_DEVELOPER_SOLUTION.md` - Apple Music setup
- `AUTHENTICATION_SOLUTION.md` - Apple Music auth
- `SETUP_MUSICKIT_IDENTIFIER.md` - Apple Music MusicKit
- `github_issue_spatial_audio.md` - Apple Music bug report
- `github_issue_spatial_audio_UPDATED.md` - Apple Music bug report

**Python Scripts**:
- `apple_music_debug_patch.py`
- `apple_music_playlist_sync_fix.py`
- `apple_music_streaming_pagination_fix.py`
- `apple_music_unicode_fix.py`
- `apply_streaming_fix.py`
- `debug_apple_playlists.py`
- `emergency_fix.py`
- `export_all_artists.py`
- `extract_app_token.py`
- `final_test.py`
- `fix_playlist_sync.py`
- `force_playlist_sync.py`
- `generate_final_token.py`
- `generate_musickit_token.py`
- `generate_musickit_token_fixed.py`
- `generate_token_now.py`
- `list_all_artists.py`
- `nuclear_reset.py`
- `quick_playlist_fix.py`
- `quick_token.py`
- `spatial_audio_patch.py`
- `streaming_fix_patch.py`
- `test_apple_api_directly.py`
- `test_apple_music_auth.py`
- `test_apple_playlists_directly.py`
- `test_unicode_handling.py`
- `test_with_tokens.py`

**Shell Scripts**:
- `run_playlist_debug.sh`
- `verify_bug.sh`

**Tokens/Credentials** (KEEP, but document separately):
- `AuthKey_67B66GRRLJ.p8` - Apple Music private key (DO NOT COMMIT)
- `musickit_token_20251024_222619.txt` - Apple Music token (DO NOT COMMIT)

**Patches**:
- Move entire `patches/` directory (Apple Music fixes)

**Web UI**:
- Move entire `web_ui_enhancements/` directory (Apple Music UI)

**Validation**:
- Move entire `validation/` directory (Apple Music validation)

---

### Category 2: Obsolete Alexa OAuth Server Approach (ARCHITECTURAL DUPLICATION)

**Why Obsolete**: This approach creates a separate OAuth server, duplicating functionality already in `/config/custom_components/alexa/`.

**Archive Location**: `archives/alexa-oauth-server-approach/`

**Files to Move**:

**Core OAuth Server** (THE OBSOLETE APPROACH):
- `alexa_oauth_endpoints.py` - ⚠️ CRITICAL: This is the entire obsolete OAuth SERVER
- `auth_server.py` - OAuth server wrapper
- `oauth_server_debug.py` - OAuth server debugging
- `deploy_oauth_endpoints.py` - Deployment script
- `deploy_robust_oauth.sh` - Deployment script
- `start_oauth_background.sh` - Startup script
- `start_oauth_server.py` - Startup script
- `start_oauth_server.sh` - Startup script
- `robust_oauth_startup.py` - Startup logic
- `register_oauth_routes.py` - Route registration
- `oauth_clients.json` - OAuth client config
- `docker-compose.yml` - Docker deployment

**Documentation** (explaining the obsolete approach):
- `ALEXA_OAUTH_INTEGRATION_PROPER.md` - OAuth server architecture
- `alexa_oauth_integration_patch.txt` - OAuth server patch
- `OAUTH_CRASH_DIAGNOSIS.md` - OAuth server debugging
- `OAUTH_DECISION_TREE.md` - OAuth approach decisions
- `OAUTH_IMPLEMENTATION_STATUS.md` - OAuth server status
- `OAUTH_SECURITY_ARCHITECTURE.md` - OAuth server security
- `OAUTH_SECURITY_EXECUTIVE_SUMMARY.md` - OAuth server security
- `OAUTH_SECURITY_INDEX.md` - OAuth server security
- `URGENT_FIX_ALEXA_URL.md` - OAuth server fixes
- `caddy_deploy_guide.md` - Reverse proxy setup
- `DOCKER_CRISIS_SUMMARY.md` - Docker deployment issues
- `diagnose_oauth_crash.sh` - Debugging script

**Research Documents** (exploring Alexa OAuth options):
- `ALEXA_AUTH_ANALYSIS.md`
- `ALEXA_AUTH_EXECUTIVE_SUMMARY.md`
- `ALEXA_AUTH_QUICK_REFERENCE.md`
- `ALEXA_AUTH_SUMMARY.md`
- `ALEXA_RESEARCH_INDEX.md`
- `ALEXA_SKILL_OAUTH_RESEARCH_2025.md`
- `ALEXA_SKILL_QUICK_DECISION.md`
- `ALEXA_INTEGRATION_DOCUMENTATION_INDEX_FINAL.md`
- `ALEXA_INTEGRATION_VISUAL_GUIDE.md`
- `ALEXA_OAUTH_DOCUMENTATION_INDEX.md`

**HA Cloud Research** (alternative approach):
- `HA_CLOUD_ALEXA_INTEGRATION_RESEARCH.md`
- `HA_CLOUD_ALEXA_MASTER_PLAN.md`
- `HA_CLOUD_ALEXA_QUICK_REFERENCE.md`
- `NABU_CASA_TEST_READY.md`

**Why Archive This**:
The `alexa_oauth_endpoints.py` approach creates a separate OAuth server to handle Alexa authentication. However:
1. ✅ Home Assistant's Alexa integration ALREADY handles OAuth2 (deployed on haboxhill.local)
2. ❌ Creating a second OAuth server duplicates functionality
3. ❌ Has security vulnerabilities (hardcoded user, no actual Login with Amazon)
4. ✅ The correct approach is to ADD smart home handler to existing HA Alexa integration

**README for Archive** (`archives/alexa-oauth-server-approach/README.md`):
```markdown
# Obsolete: Alexa OAuth Server Approach

**Date Archived**: 2025-11-02
**Reason**: Architectural duplication

## What This Was

This directory contains an OAuth2 server implementation (`alexa_oauth_endpoints.py`) designed to handle Alexa authentication separately from Home Assistant.

## Why Obsolete

After deployment analysis, we discovered:
1. Home Assistant's Alexa integration (`/config/custom_components/alexa/`) already handles OAuth2
2. Creating a second OAuth server duplicates functionality
3. The OAuth server approach has security gaps (hardcoded user_id)
4. The correct solution is simpler: add smart home handler to existing HA integration

## Correct Architecture

```
Alexa → HA Alexa Integration → Smart Home Handler → Music Assistant
         (OAuth2 already done)   (missing piece)
```

Not:

```
Alexa → Separate OAuth Server → Music Assistant
         (this entire directory)
```

## Historical Value

This code demonstrates:
- OAuth2 + PKCE server-side implementation
- Alexa Smart Home skill webhook handling
- But in wrong architectural layer (should be IN Home Assistant, not separate)

## Related Documents

- `/INTEGRATION_STRATEGY.md` - Correct architecture
- `/APPLY_ALEXA_OAUTH2_FIXES.md` - Security analysis of this approach
- `/Users/jason/projects/alexa-oauth2/` - The CORRECT OAuth implementation (HA integration)
```

---

### Category 3: Historical Session Documentation (ARCHIVE BUT PRESERVE)

**Why Archive**: These are interim status reports and session summaries from exploration phase. Valuable for understanding project evolution, but not needed for current work.

**Archive Location**: `archives/historical-sessions/`

**Files to Move**:
- `ARCHITECTURE_PIVOT_SUMMARY_2025-10-27.md`
- `AUDIT_SUMMARY_ACTION_ITEMS.md`
- `AUDIT_VISUAL_SUMMARY.md`
- `CRITICAL_ISSUE_INDEX.md`
- `CRITICAL_ISSUE_SUMMARY.md`
- `CURRENT_STATUS.md` (outdated status)
- `DELIVERABLES_SUMMARY_2025-10-27.md`
- `DOCUMENTATION_AUDIT_REPORT_2025-10-26.md`
- `DOCUMENTATION_ORGANIZATION_COMPLETE.md`
- `DOCUMENTATION_QUICK_MAP.md`
- `DOCUMENTATION_REALIGNMENT_REPORT.md`
- `DOCUMENTATION_REMEDIATION_GUIDE.md`
- `DOCUMENTATION_SYNTHESIS_COMPLETE.md`
- `EXECUTION_COMPLETE_NEXT_STEPS.md`
- `EXECUTIVE_BRIEF_ALEXA_INTEGRATION.md`
- `FINAL_SUMMARY.md`
- `FOR_TOMORROW_MORNING.md`
- `IMPLEMENTATION_STATUS_2025-10-27.md`
- `MISSION_BRIEF_FOR_TEAMS.md`
- `PHASE_2_FINDINGS.md`
- `PHASE_2_STATUS_2025-10-26.md`
- `QUICK_FIX_GUIDE.md`
- `QUICK_START_CARD.md`
- `REALIGNMENT_SESSION_SUMMARY.md`
- `REFACTORING_EXECUTIVE_SUMMARY.md`
- `SECURITY_ANALYSIS.md`
- `SESSION_SUMMARY_2025-10-27.md`
- `SOLUTION_SUMMARY.md`
- `STRATEGIC_NARRATIVE_ALEXA_INTEGRATION.md`
- `STRATEGIC_REFACTORING_ANALYSIS_2025-11-02.md`
- `SUMMARY.md`

**Screenshots**:
- `CleanShot 2025-10-25 at 23.25.51@2x.png`
- Move to `archives/historical-sessions/screenshots/`

---

### Category 4: Working Directories (REORGANIZE)

**`workspace/` directory**:
- Review contents
- Archive anything Apple Music related
- Keep Alexa integration work-in-progress

**`scripts/` directory**:
- Archive Apple Music scripts
- Keep Alexa integration scripts (if any)

**`docs/` directory**:
- Review current structure
- Keep only relevant documentation
- Move obsolete docs to archives

**`__pycache__/` directory**:
- Delete (generated files, should be in .gitignore)

---

### Category 5: KEEP ACTIVE (Core Project Files)

**Already Committed** (✅):
- `.gitignore`
- `INTEGRATION_STRATEGY.md` - ✅ Correct architecture
- `APPLY_ALEXA_OAUTH2_FIXES.md` - ✅ Security analysis

**To Keep and Update**:
- `README.md` - Rewrite to explain current state
- `PROJECT.md` - Update to reflect new architecture
- `DECISIONS.md` - Keep but review/update
- `SESSION_LOG.md` - Keep ongoing log
- `00_QUICKSTART.md` - Update to reflect current state

**Deployment Documentation** (if relevant):
- `DEPLOYMENT_PLAN_NATIVE.md` - Review, keep if relevant
- `DEPLOY_DEBUG_SERVER.md` - Review, archive if obsolete
- `DEVELOPER_IMPLEMENTATION_GUIDE_ALEXA_INTEGRATION.md` - Review, keep if useful
- `00_IMPLEMENTATION_READY.md` - Review status

**Miscellaneous**:
- `DIAGNOSIS.md` - Review, archive if obsolete
- `UI_MOCKUP.txt` - Review, keep if relevant

---

## Archive Structure

```
MusicAssistantApple/
├── archives/
│   ├── apple-music-integration/
│   │   ├── README.md                    # Why this was archived
│   │   ├── documentation/               # All Apple Music docs
│   │   ├── scripts/                     # All Apple Music scripts
│   │   ├── patches/                     # Apple Music patches
│   │   ├── web_ui_enhancements/        # Apple Music UI work
│   │   └── validation/                  # Apple Music validation
│   │
│   ├── alexa-oauth-server-approach/
│   │   ├── README.md                    # Why this approach was abandoned
│   │   ├── alexa_oauth_endpoints.py    # THE obsolete OAuth server
│   │   ├── deployment/                  # Docker, scripts, configs
│   │   ├── documentation/               # OAuth server docs
│   │   └── research/                    # Alexa OAuth research
│   │
│   └── historical-sessions/
│       ├── README.md                    # Session summaries index
│       ├── architecture-pivots/         # Architecture decision points
│       ├── documentation-audits/        # Doc reorganization sessions
│       └── screenshots/                 # Visual documentation
│
├── docs/
│   └── 00_ARCHITECTURE/
│       ├── CROSS_REFERENCE_ALEXA_OAUTH2.md  # How projects integrate
│       └── SYSTEM_OVERVIEW.md               # Current architecture
│
├── .gitignore                          # ✅ Already committed
├── INTEGRATION_STRATEGY.md            # ✅ Already committed
├── APPLY_ALEXA_OAUTH2_FIXES.md        # ✅ Already committed
├── README.md                           # NEW: Current state
├── PROJECT.md                          # UPDATED: New architecture
├── 00_QUICKSTART.md                    # UPDATED: Quick start
├── DECISIONS.md                        # UPDATED: Key decisions
└── SESSION_LOG.md                      # ONGOING: Activity log
```

---

## Execution Steps

### Step 1: Create Archive Directories

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

# Create archive structure
mkdir -p archives/apple-music-integration/{documentation,scripts,patches,web_ui_enhancements,validation}
mkdir -p archives/alexa-oauth-server-approach/{deployment,documentation,research}
mkdir -p archives/historical-sessions/{architecture-pivots,documentation-audits,screenshots}
```

### Step 2: Move Apple Music Integration Files

```bash
# Documentation
mv 00_START_HERE_PLAYLIST_FIX.md \
   PLAYLIST_FIX_README.md \
   PLAYLIST_FIX_STATUS.md \
   README_PLAYLIST_FIX.md \
   PLAYLIST_SYNC_ANALYSIS.md \
   UNICODE_FIX_INDEX.md \
   UNICODE_FIX_PATCH.md \
   UNICODE_FIX_QUICK_REFERENCE.txt \
   UNICODE_FIX_README.md \
   UNICODE_FIX_SUMMARY.md \
   SPATIAL_AUDIO_EXPLANATION.md \
   SPATIAL_AUDIO_TRUTH.md \
   APPLY_STREAMING_PAGINATION_PATCH.md \
   PAGINATION_ISSUE_ANALYSIS.md \
   ALPHABETICAL_NAVIGATION_README.md \
   ALPHABETICAL_NAVIGATION_SOLUTION.md \
   APPLE_DEVELOPER_SOLUTION.md \
   AUTHENTICATION_SOLUTION.md \
   SETUP_MUSICKIT_IDENTIFIER.md \
   github_issue_spatial_audio.md \
   github_issue_spatial_audio_UPDATED.md \
   archives/apple-music-integration/documentation/

# Scripts
mv apple_music_*.py \
   apply_streaming_fix.py \
   debug_apple_playlists.py \
   emergency_fix.py \
   export_all_artists.py \
   extract_app_token.py \
   final_test.py \
   fix_playlist_sync.py \
   force_playlist_sync.py \
   generate_*.py \
   list_all_artists.py \
   nuclear_reset.py \
   quick_playlist_fix.py \
   quick_token.py \
   spatial_audio_patch.py \
   streaming_fix_patch.py \
   test_apple_*.py \
   test_unicode_handling.py \
   test_with_tokens.py \
   run_playlist_debug.sh \
   verify_bug.sh \
   archives/apple-music-integration/scripts/

# Directories
mv patches/ archives/apple-music-integration/
mv web_ui_enhancements/ archives/apple-music-integration/
mv validation/ archives/apple-music-integration/
```

### Step 3: Move Alexa OAuth Server Files

```bash
# Core OAuth server files
mv alexa_oauth_endpoints.py \
   auth_server.py \
   oauth_server_debug.py \
   oauth_clients.json \
   docker-compose.yml \
   archives/alexa-oauth-server-approach/

# Deployment scripts
mv deploy_oauth_endpoints.py \
   deploy_robust_oauth.sh \
   start_oauth_*.sh \
   start_oauth_*.py \
   robust_oauth_startup.py \
   register_oauth_routes.py \
   archives/alexa-oauth-server-approach/deployment/

# OAuth server documentation
mv ALEXA_OAUTH_INTEGRATION_PROPER.md \
   alexa_oauth_integration_patch.txt \
   OAUTH_CRASH_DIAGNOSIS.md \
   OAUTH_DECISION_TREE.md \
   OAUTH_IMPLEMENTATION_STATUS.md \
   OAUTH_SECURITY_ARCHITECTURE.md \
   OAUTH_SECURITY_EXECUTIVE_SUMMARY.md \
   OAUTH_SECURITY_INDEX.md \
   URGENT_FIX_ALEXA_URL.md \
   caddy_deploy_guide.md \
   DOCKER_CRISIS_SUMMARY.md \
   diagnose_oauth_crash.sh \
   archives/alexa-oauth-server-approach/documentation/

# Research documents
mv ALEXA_AUTH_*.md \
   ALEXA_RESEARCH_INDEX.md \
   ALEXA_SKILL_*.md \
   ALEXA_INTEGRATION_*.md \
   ALEXA_OAUTH_DOCUMENTATION_INDEX.md \
   HA_CLOUD_ALEXA_*.md \
   NABU_CASA_TEST_READY.md \
   archives/alexa-oauth-server-approach/research/
```

### Step 4: Move Historical Session Files

```bash
mv ARCHITECTURE_PIVOT_SUMMARY_2025-10-27.md \
   archives/historical-sessions/architecture-pivots/

mv DOCUMENTATION_*.md \
   archives/historical-sessions/documentation-audits/

mv AUDIT_*.md \
   CRITICAL_ISSUE_*.md \
   CURRENT_STATUS.md \
   DELIVERABLES_SUMMARY_2025-10-27.md \
   EXECUTION_COMPLETE_NEXT_STEPS.md \
   EXECUTIVE_BRIEF_ALEXA_INTEGRATION.md \
   FINAL_SUMMARY.md \
   FOR_TOMORROW_MORNING.md \
   IMPLEMENTATION_STATUS_2025-10-27.md \
   MISSION_BRIEF_FOR_TEAMS.md \
   PHASE_2_*.md \
   QUICK_FIX_GUIDE.md \
   QUICK_START_CARD.md \
   REALIGNMENT_SESSION_SUMMARY.md \
   REFACTORING_EXECUTIVE_SUMMARY.md \
   SECURITY_ANALYSIS.md \
   SESSION_SUMMARY_2025-10-27.md \
   SOLUTION_SUMMARY.md \
   STRATEGIC_*.md \
   SUMMARY.md \
   archives/historical-sessions/

mv "CleanShot 2025-10-25 at 23.25.51@2x.png" \
   archives/historical-sessions/screenshots/
```

### Step 5: Clean Up Generated Files

```bash
# Remove Python cache
rm -rf __pycache__/

# Verify .gitignore includes common generated files
grep -E "(__pycache__|*.pyc|*.pyo|.DS_Store)" .gitignore
```

### Step 6: Create Archive README Files

Create `archives/apple-music-integration/README.md`:
```markdown
# Apple Music Integration Work (Archived)

**Date Archived**: 2025-11-02
**Reason**: Different problem than current project

## What This Was

This directory contains code and documentation for integrating Apple Music API with Home Assistant's Music Assistant. The work focused on:
- Apple Music playlist synchronization
- Unicode handling in track names
- Spatial audio metadata
- Streaming pagination
- MusicKit token generation

## Why Archived

The MusicAssistantApple project pivoted to a different architecture:
- **Original goal**: Direct Apple Music API integration
- **Actual need**: Alexa voice control for Music Assistant
- **Solution**: Smart home handler in Home Assistant (not Apple Music API)

## What Was Learned

- Apple Music API challenges (Unicode, pagination, spatial audio)
- MusicKit authentication flow
- Home Assistant integration patterns
- Music Assistant provider architecture

## Files Preserved

- `documentation/` - All Apple Music integration docs
- `scripts/` - Python scripts for Apple Music API
- `patches/` - Code patches for Apple Music issues
- `web_ui_enhancements/` - UI improvements for playlist management
- `validation/` - Test scripts and validation tools
```

Create `archives/alexa-oauth-server-approach/README.md` (content already defined above).

Create `archives/historical-sessions/README.md`:
```markdown
# Historical Session Documentation

**Date Archived**: 2025-11-02

## What This Contains

Session summaries, status reports, and interim documentation from the project exploration phase (October 2025).

## Directory Structure

- `architecture-pivots/` - Key architectural decision points
- `documentation-audits/` - Documentation organization sessions
- `screenshots/` - Visual documentation snapshots

## Why Preserved

These documents show the evolution of understanding from:
1. Apple Music API integration approach
2. Separate OAuth server approach
3. **Final correct architecture**: Alexa → HA integration → Music Assistant

## Key Pivot Points

1. **2025-10-25**: Realized Apple Music API not needed
2. **2025-10-27**: Explored separate OAuth server approach
3. **2025-11-02**: Discovered correct architecture (extend HA Alexa integration)

## Related

- `/INTEGRATION_STRATEGY.md` - Final correct architecture
- `/archives/alexa-oauth-server-approach/` - Obsolete OAuth server
- `/archives/apple-music-integration/` - Original Apple Music work
```

---

## Verification

After execution, verify:

```bash
# Should show clean root with only active files
ls -1 *.md *.py 2>/dev/null

# Expected: README.md, PROJECT.md, DECISIONS.md, SESSION_LOG.md,
#           00_QUICKSTART.md, INTEGRATION_STRATEGY.md,
#           APPLY_ALEXA_OAUTH2_FIXES.md

# Verify archives
ls -R archives/

# Verify git status
git status

# Should show only untracked: README.md, PROJECT.md, DECISIONS.md,
# SESSION_LOG.md, 00_QUICKSTART.md, docs/, archives/
```

---

## Next Steps After Cleanup

1. **Create new README.md** - Explain current project state
2. **Update PROJECT.md** - Reflect correct architecture
3. **Update 00_QUICKSTART.md** - Quick orientation to current state
4. **Create docs/00_ARCHITECTURE/CROSS_REFERENCE_ALEXA_OAUTH2.md** - Integration guide
5. **Git commit** - Stage appropriate files (NOT credentials!)

---

## Credentials Handling

**DO NOT COMMIT**:
- `AuthKey_67B66GRRLJ.p8` - Apple Music private key
- `musickit_token_20251024_222619.txt` - Apple Music token
- Any `oauth_clients.json` with real secrets

**Verify .gitignore includes**:
```gitignore
# Credentials
*.p8
*token*.txt
oauth_clients.json
credentials.json

# Apple Music
AuthKey_*
musickit_token_*
```

---

## Success Criteria

**After cleanup**:
- [ ] Root directory has <15 files (down from ~130)
- [ ] All Apple Music work in `archives/apple-music-integration/`
- [ ] All OAuth server code in `archives/alexa-oauth-server-approach/`
- [ ] All session docs in `archives/historical-sessions/`
- [ ] Clean git status (only relevant untracked files)
- [ ] README.md explains current state clearly
- [ ] PROJECT.md reflects correct architecture
- [ ] docs/00_ARCHITECTURE/ has cross-reference to alexa-oauth2

**Project should be**:
- Easy to understand in 2 minutes (README.md + 00_QUICKSTART.md)
- Clear about relationship to alexa-oauth2 project
- Ready for next phase: Implement smart home handler

---

**Document Status**: READY TO EXECUTE
**Estimated Time**: 30 minutes
**Risk**: LOW (all moves to archives, nothing deleted)
