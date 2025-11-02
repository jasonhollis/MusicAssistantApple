# Git Commit Recommendations

**Date**: 2025-11-02
**Purpose**: Guide for staging and committing cleaned-up project files
**Status**: READY TO EXECUTE

---

## Current Git Status

**Already Committed** (initial commit 17f10f0):
- `.gitignore`
- `INTEGRATION_STRATEGY.md`
- `APPLY_ALEXA_OAUTH2_FIXES.md`

**Untracked After Cleanup**:
- `ARCHIVE_PLAN.md` - Cleanup documentation
- `README.md` - Updated project overview
- `PROJECT.md` - Updated goals and architecture
- `DECISIONS.md` - Existing decision log (needs review/update)
- `SESSION_LOG.md` - Activity log (keep updated)
- `00_QUICKSTART.md` - Quick start guide (needs review/update)
- `00_IMPLEMENTATION_READY.md` - Status doc (review if still relevant)
- `docs/` - Architecture documentation
- `archives/` - Historical work (learning resources)
- `workspace/` - Working files (review contents)

---

## Files to NEVER Commit (Security)

**Credentials and Tokens**:
- `AuthKey_67B66GRRLJ.p8` - Apple Music private key (KEEP LOCAL)
- `musickit_token_20251024_222619.txt` - Apple Music token (KEEP LOCAL)
- Any `oauth_clients.json` with real secrets (KEEP LOCAL)
- Any `credentials.json` files (KEEP LOCAL)

**Verify .gitignore includes**:
```gitignore
# Credentials (CRITICAL - Never commit these)
*.p8
*token*.txt
oauth_clients.json
credentials.json
AuthKey_*
musickit_token_*

# Apple Music secrets
*.p8
musickit_token_*.txt

# Generated files
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# Workspace (optional - depends on if contains secrets)
workspace/*.json
workspace/*.txt
workspace/*token*
workspace/*credential*
```

---

## Recommended Commit Sequence

### Commit 1: Project cleanup and reorganization

**Message**:
```
docs: Reorganize project after architecture discovery

- Archive obsolete Apple Music API integration work
- Archive obsolete OAuth server approach
- Archive historical session documentation
- Update README.md to reflect correct architecture
- Update PROJECT.md with implementation plan
- Add architecture cross-reference documentation

Architecture discovered:
- HA Alexa integration already deployed (OAuth2+PKCE)
- Music Assistant integration already deployed
- Need smart home handler (~200 lines), not OAuth server (~800 lines)

Archives preserve learning history but clarify current direction.
```

**Files to stage**:
```bash
git add ARCHIVE_PLAN.md
git add README.md
git add PROJECT.md
git add docs/00_ARCHITECTURE/CROSS_REFERENCE_ALEXA_OAUTH2.md
git add archives/
```

**Verification before commit**:
```bash
# Verify no credentials being committed
git diff --cached | grep -E "(AuthKey|token.*txt|oauth_clients\.json|credentials\.json)"
# Should return NOTHING

# Verify archive structure
ls -la archives/*/
# Should show apple-music-integration/, alexa-oauth-server-approach/, historical-sessions/

# Verify no Python bytecode
git diff --cached | grep -E "(__pycache__|\.pyc|\.pyo)"
# Should return NOTHING
```

---

### Commit 2: Update decision log and quickstart

**Message**:
```
docs: Update DECISIONS.md and 00_QUICKSTART.md

- Document key architectural decisions
- Explain why OAuth server approach was abandoned
- Explain why Apple Music API integration was archived
- Update quickstart for current project state

Decisions documented:
1. Extend HA integration vs separate OAuth server
2. Use MA's Apple Music provider vs direct API
3. Smart home handler location and design
```

**Files to stage** (after reviewing/updating):
```bash
git add DECISIONS.md
git add 00_QUICKSTART.md
```

**Before staging, review these files**:
1. `DECISIONS.md` - Does it document the three key decisions?
2. `00_QUICKSTART.md` - Does it reflect current architecture?

---

### Commit 3: Update session log (optional - depends on content)

**Message**:
```
docs: Update session log with cleanup activities

- Documented project reorganization
- Archived obsolete approaches
- Clarified correct architecture
```

**Files to stage**:
```bash
git add SESSION_LOG.md
```

**Note**: Only commit if SESSION_LOG.md has meaningful updates. Otherwise, keep it as working file for ongoing session notes.

---

## What NOT to Commit (Yet)

### Implementation Status Docs (Premature)

**`00_IMPLEMENTATION_READY.md`**:
- Review first - is implementation actually ready?
- May be obsolete given architecture change
- Consider archiving or updating before committing

### Workspace Directory

**`workspace/`**:
- Review contents first
- Likely contains work-in-progress files
- May contain temporary credentials or tokens
- Add to .gitignore if sensitive
- Commit only if contains valuable design docs

**Decision**: Review `workspace/` contents before committing anything from it.

### Credentials (NEVER)

These files are already moved to archives but ensure they're in .gitignore:
- `AuthKey_67B66GRRLJ.p8` (in apple-music-integration archive)
- `musickit_token_20251024_222619.txt` (in apple-music-integration archive)

---

## Pre-Commit Checklist

Before each `git commit`, verify:

**Security** 🔒:
- [ ] No credentials (*.p8, *token*.txt, credentials.json)
- [ ] No API keys or secrets
- [ ] No oauth_clients.json with real client secrets
- [ ] No hardcoded passwords or tokens

**Generated Files** 🗑️:
- [ ] No __pycache__ directories
- [ ] No *.pyc, *.pyo files
- [ ] No .DS_Store files
- [ ] No IDE config (.vscode/, .idea/)

**Content Quality** ✅:
- [ ] Commit message follows convention (type: description)
- [ ] Files are logically grouped (one concern per commit)
- [ ] Documentation is accurate and current
- [ ] No TODO or FIXME comments without context

**Architecture Compliance** 🏛️:
- [ ] Documentation follows layer structure (00-05)
- [ ] No circular dependencies
- [ ] Inner layers don't reference outer layers
- [ ] Abstractions separated from implementations

---

## Commit Message Conventions

Follow conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `docs:` - Documentation changes
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructure without behavior change
- `test:` - Add or update tests
- `chore:` - Maintenance tasks

**Scopes** (optional):
- `arch` - Architecture documentation
- `oauth` - OAuth-related changes
- `ma` - Music Assistant integration
- `cleanup` - Cleanup and reorganization

**Examples**:
```
docs(arch): Add cross-reference to alexa-oauth2 project

docs(cleanup): Archive obsolete OAuth server approach

feat(ma): Implement smart home handler for Music Assistant

test(ma): Add unit tests for directive routing
```

---

## Post-Commit Verification

After each commit, verify:

```bash
# Check commit was created
git log --oneline -1

# Verify what was committed
git show HEAD --stat

# Verify no credentials in commit
git show HEAD | grep -E "(AuthKey|token|secret|password|credential)"
# Should return NOTHING or only references in docs

# Verify file structure
git ls-tree -r HEAD --name-only | head -20
```

---

## Remote Repository Considerations

### If Pushing to GitHub/GitLab

**Before first push**:
1. Review ALL commit history for credentials
2. Verify .gitignore is correct
3. Consider using git-secrets or similar tool
4. Set up branch protection rules

**GitHub Repository Settings**:
- Enable "Require pull request reviews before merging"
- Enable "Require status checks to pass"
- Protect main branch from force pushes
- Enable secret scanning

**GitLab Repository Settings**:
- Enable "Prevent secrets"
- Enable "Require approval from code owners"
- Protect main branch
- Enable merge request approvals

---

### If Keeping Local Only

**Backup Strategy**:
```bash
# Create local backup
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects"
tar -czf MusicAssistantApple-backup-$(date +%Y%m%d).tar.gz MusicAssistantApple/

# Verify backup
tar -tzf MusicAssistantApple-backup-*.tar.gz | head -20
```

**Time Machine Considerations**:
- iCloud Drive is already versioned (File Provider)
- Time Machine backs up iCloud Drive local files
- Git provides additional version control
- Keep sensitive files in .gitignore to avoid iCloud sync

---

## Rollback Procedures

### Undo Last Commit (Before Push)

**Keep changes, undo commit**:
```bash
git reset --soft HEAD~1
# Changes stay staged, commit undone
```

**Undo changes and commit**:
```bash
git reset --hard HEAD~1
# WARNING: Loses all changes in last commit
```

---

### Remove Accidentally Committed File

**If not yet pushed**:
```bash
# Remove from git but keep in filesystem
git rm --cached <file>
git commit --amend --no-edit

# Remove from git and filesystem
git rm <file>
git commit --amend --no-edit
```

**If already pushed** (DANGEROUS):
```bash
# Contact everyone who pulled the repo
# Use git filter-branch or BFG Repo-Cleaner
# See GitHub's guide: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
```

---

### Restore Archived File

**From archive to working directory**:
```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

# Copy file from archive
cp archives/alexa-oauth-server-approach/alexa_oauth_endpoints.py .

# Review and adapt as needed
# Do NOT blindly recommit old code
```

---

## Suggested First Commit Commands

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

# Verify .gitignore is correct
cat .gitignore

# Check current status
git status

# Stage files for first commit (cleanup)
git add ARCHIVE_PLAN.md
git add README.md
git add PROJECT.md
git add docs/00_ARCHITECTURE/CROSS_REFERENCE_ALEXA_OAUTH2.md
git add archives/

# Verify no credentials
git diff --cached | grep -E "(AuthKey|token.*txt|oauth_clients|credentials)"

# Should return NOTHING - if it finds anything, investigate and exclude

# Review what will be committed
git diff --cached --stat

# Commit
git commit -m "docs: Reorganize project after architecture discovery

- Archive obsolete Apple Music API integration work
- Archive obsolete OAuth server approach
- Archive historical session documentation
- Update README.md to reflect correct architecture
- Update PROJECT.md with implementation plan
- Add architecture cross-reference documentation

Architecture discovered:
- HA Alexa integration already deployed (OAuth2+PKCE)
- Music Assistant integration already deployed
- Need smart home handler (~200 lines), not OAuth server (~800 lines)

Archives preserve learning history but clarify current direction."

# Verify commit
git log --oneline -1
git show HEAD --stat
```

---

## Summary

### Safe to Commit Now ✅:
- `ARCHIVE_PLAN.md` - Cleanup documentation
- `README.md` - Updated overview
- `PROJECT.md` - Updated architecture
- `docs/00_ARCHITECTURE/CROSS_REFERENCE_ALEXA_OAUTH2.md` - Integration guide
- `archives/` - Historical work (no credentials)

### Review Before Committing ⚠️:
- `DECISIONS.md` - Update with key decisions first
- `00_QUICKSTART.md` - Verify reflects current state
- `00_IMPLEMENTATION_READY.md` - May be obsolete
- `SESSION_LOG.md` - Only if has meaningful updates
- `workspace/` - Review contents for sensitivity

### NEVER Commit ❌:
- `*.p8` - Apple private keys
- `*token*.txt` - Generated tokens
- `oauth_clients.json` - OAuth secrets
- `credentials.json` - Any credentials
- `__pycache__/` - Python bytecode
- `.DS_Store` - OS files

### Commit Sequence:
1. **Commit 1**: Cleanup (archives, README, PROJECT, docs)
2. **Commit 2**: Decisions and quickstart (after review/update)
3. **Commit 3**: Session log (optional)

---

**Document Status**: COMPLETE
**Ready to Execute**: YES
**Security Review**: REQUIRED (check for credentials before each commit)
