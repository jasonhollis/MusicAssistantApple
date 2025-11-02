#!/bin/bash
#
# Apply Alphabetical Navigation Enhancement to Music Assistant
#
# This script applies the backend API changes and frontend UI enhancements
# to enable A-Z navigation in the artist library view.
#
# Usage: ./apply_alphabetical_navigation.sh [OPTIONS]
#
# Options:
#   --backup-only    Only create backups, don't apply changes
#   --dry-run        Show what would be done without making changes
#   --no-backup      Skip creating backups (dangerous!)
#   --help           Show this help message
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVER_DIR="$PROJECT_DIR/server-2.6.0"
BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"

# Flags
DRY_RUN=false
BACKUP_ONLY=false
NO_BACKUP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --backup-only)
            BACKUP_ONLY=true
            shift
            ;;
        --no-backup)
            NO_BACKUP=true
            shift
            ;;
        --help)
            grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# //; s/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verify prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if server directory exists
    if [ ! -d "$SERVER_DIR" ]; then
        log_error "Server directory not found: $SERVER_DIR"
        exit 1
    fi

    # Check if artists.py exists
    if [ ! -f "$SERVER_DIR/music_assistant/controllers/media/artists.py" ]; then
        log_error "Artists controller not found"
        exit 1
    fi

    # Check if patch file exists
    if [ ! -f "$PROJECT_DIR/patches/artists_alphabetical_navigation.patch" ]; then
        log_error "Patch file not found"
        exit 1
    fi

    # Check if JavaScript file exists
    if [ ! -f "$PROJECT_DIR/web_ui_enhancements/alphabetical_navigation.js" ]; then
        log_error "JavaScript enhancement file not found"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Create backups
create_backups() {
    if [ "$NO_BACKUP" = true ]; then
        log_warning "Skipping backups (--no-backup flag set)"
        return
    fi

    log_info "Creating backups in: $BACKUP_DIR"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would create: $BACKUP_DIR"
        log_info "[DRY RUN] Would backup: artists.py"
        return
    fi

    mkdir -p "$BACKUP_DIR"

    # Backup artists.py
    cp "$SERVER_DIR/music_assistant/controllers/media/artists.py" \
       "$BACKUP_DIR/artists.py.backup"

    # Backup webserver.py if it exists
    if [ -f "$SERVER_DIR/music_assistant/controllers/webserver.py" ]; then
        cp "$SERVER_DIR/music_assistant/controllers/webserver.py" \
           "$BACKUP_DIR/webserver.py.backup"
    fi

    log_success "Backups created"
}

# Apply patch to artists.py
apply_backend_patch() {
    log_info "Applying backend patch to artists.py..."

    local artists_file="$SERVER_DIR/music_assistant/controllers/media/artists.py"
    local patch_file="$PROJECT_DIR/patches/artists_alphabetical_navigation.patch"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would apply patch: $patch_file"
        log_info "[DRY RUN] Would modify: $artists_file"
        return
    fi

    # Try to apply patch
    if patch -p1 -d "$SERVER_DIR" --dry-run < "$patch_file" &>/dev/null; then
        patch -p1 -d "$SERVER_DIR" < "$patch_file"
        log_success "Backend patch applied successfully"
    else
        log_warning "Patch couldn't be applied automatically"
        log_info "Manual steps required:"
        log_info "  1. Open: $artists_file"
        log_info "  2. Add the three new methods from the patch"
        log_info "  3. Register API commands in __init__()"
    fi

    # Verify Python syntax
    if python3 -m py_compile "$artists_file" 2>/dev/null; then
        log_success "Python syntax validated"
    else
        log_error "Python syntax error detected!"
        log_error "Please review changes in: $artists_file"
        exit 1
    fi
}

# Install frontend JavaScript
install_frontend_script() {
    log_info "Installing frontend enhancement script..."

    local target_dir="$SERVER_DIR/music_assistant/web_ui_enhancements"
    local source_js="$PROJECT_DIR/web_ui_enhancements/alphabetical_navigation.js"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would create: $target_dir"
        log_info "[DRY RUN] Would copy: alphabetical_navigation.js"
        return
    fi

    # Create directory
    mkdir -p "$target_dir"

    # Copy JavaScript file
    cp "$source_js" "$target_dir/alphabetical_navigation.js"
    chmod 644 "$target_dir/alphabetical_navigation.js"

    log_success "Frontend script installed"
}

# Test API endpoints
test_api_endpoints() {
    log_info "Testing API endpoints..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would test API endpoints"
        return
    fi

    # Check if Music Assistant is running
    if ! curl -s http://localhost:8095/api >/dev/null 2>&1; then
        log_warning "Music Assistant doesn't appear to be running"
        log_info "Start Music Assistant and test manually with:"
        log_info "  curl http://localhost:8095/api/music/artists/letter_counts"
        return
    fi

    # Test letter counts endpoint
    log_info "Testing letter_counts endpoint..."
    if curl -s http://localhost:8095/api/music/artists/letter_counts | grep -q '"A"'; then
        log_success "letter_counts endpoint working"
    else
        log_warning "letter_counts endpoint may not be working yet"
    fi

    # Test by_letter endpoint
    log_info "Testing by_letter endpoint..."
    if curl -s "http://localhost:8095/api/music/artists/by_letter?letter=A" | grep -q 'item_id'; then
        log_success "by_letter endpoint working"
    else
        log_warning "by_letter endpoint may not be working yet"
    fi

    log_info "Restart Music Assistant to activate new endpoints"
}

# Show next steps
show_next_steps() {
    log_success "Installation complete!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Next Steps:"
    echo ""
    echo "1. Restart Music Assistant:"
    echo "   • Docker: docker restart music-assistant"
    echo "   • Service: systemctl restart music-assistant"
    echo "   • Manual: pkill -f music_assistant && python3 -m music_assistant"
    echo ""
    echo "2. Open web UI: http://localhost:8095"
    echo ""
    echo "3. Navigate to: Library > Artists"
    echo ""
    echo "4. You should see:"
    echo "   • A-Z navigation bar at the top"
    echo "   • Search box on the right"
    echo "   • Letter counts showing number of artists"
    echo ""
    echo "5. Test functionality:"
    echo "   • Click 'J' to see only J artists"
    echo "   • Click 'Z' to see only Z artists (including ZZ Top)"
    echo "   • Use search box to find specific artists"
    echo ""
    echo "6. If navigation bar doesn't appear:"
    echo "   • Check browser console (F12) for errors"
    echo "   • Verify script: http://localhost:8095/web-ui-enhancements/alphabetical-navigation.js"
    echo "   • Clear browser cache and reload"
    echo ""
    if [ "$NO_BACKUP" = false ]; then
        echo "Backups saved in: $BACKUP_DIR"
        echo ""
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Rollback function
show_rollback_instructions() {
    echo ""
    echo "To rollback these changes:"
    echo ""
    echo "  cp $BACKUP_DIR/artists.py.backup \\"
    echo "     $SERVER_DIR/music_assistant/controllers/media/artists.py"
    echo ""
    echo "  rm -rf $SERVER_DIR/music_assistant/web_ui_enhancements"
    echo ""
    echo "  # Then restart Music Assistant"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Alphabetical Navigation Enhancement Installer"
    echo "  Music Assistant Web UI"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Check prerequisites
    check_prerequisites

    # Create backups
    create_backups

    if [ "$BACKUP_ONLY" = true ]; then
        log_success "Backup-only mode: Backups created successfully"
        exit 0
    fi

    # Apply changes
    apply_backend_patch
    install_frontend_script

    # Test endpoints (if running)
    test_api_endpoints

    # Show next steps
    show_next_steps

    # Show rollback instructions
    if [ "$NO_BACKUP" = false ]; then
        show_rollback_instructions
    fi
}

# Run main
main
