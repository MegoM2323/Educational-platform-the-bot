#!/bin/bash
# Git Credentials Cleanup Script
# WARNING: This rewrites git history and requires force push
# COORDINATE WITH ALL TEAM MEMBERS BEFORE EXECUTING

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==================================================================="
echo "         GIT CREDENTIALS CLEANUP - HISTORY REWRITE"
echo "==================================================================="
echo ""
echo "This script will remove .env.production from git history."
echo "Affected commit: 41a5360a21c576ccbd42868468f1b36d67b254fa"
echo ""
echo "⚠️  WARNING: This operation will:"
echo "   1. Rewrite entire git history"
echo "   2. Change all commit SHAs after the affected commit"
echo "   3. Require force push to remote repository"
echo "   4. Break any existing pull requests"
echo "   5. Require all team members to re-clone or rebase"
echo ""
echo "==================================================================="
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ ERROR: You have uncommitted changes. Commit or stash them first."
    exit 1
fi

# Verify we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  WARNING: You are on branch '$CURRENT_BRANCH', not 'main'"
    echo "   It's recommended to run this on 'main' branch"
    read -p "Continue anyway? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
fi

# Create backup
BACKUP_FILE="backup-$(date +%Y%m%d-%H%M%S).bundle"
echo "📦 Creating backup: $BACKUP_FILE"
git bundle create "$BACKUP_FILE" --all
echo "✅ Backup created successfully"
echo ""

# Check if BFG exists
BFG_PATH="$REPO_ROOT/bfg.jar"
if [ ! -f "$BFG_PATH" ]; then
    echo "📥 Downloading BFG Repo-Cleaner..."
    wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar -O "$BFG_PATH"
    echo "✅ BFG downloaded"
    echo ""
fi

# Verify Java is installed
if ! command -v java &> /dev/null; then
    echo "❌ ERROR: Java is required to run BFG. Install Java and try again."
    exit 1
fi

# Final confirmation
echo "==================================================================="
echo "READY TO EXECUTE CLEANUP"
echo "==================================================================="
echo ""
echo "The following file will be removed from ALL git history:"
echo "  - .env.production"
echo ""
echo "After this operation you MUST:"
echo "  1. Rotate all exposed credentials (see docs/CREDENTIAL_ROTATION_ESC001.md)"
echo "  2. Force push to remote: git push origin --force --all"
echo "  3. Notify all team members to re-clone or rebase their branches"
echo ""
read -p "Type 'DELETE HISTORY' to proceed: " CONFIRMATION

if [ "$CONFIRMATION" != "DELETE HISTORY" ]; then
    echo "Aborted. No changes made."
    exit 0
fi

echo ""
echo "🔥 Executing cleanup..."
echo ""

# Run BFG to delete .env.production
java -jar "$BFG_PATH" --delete-files .env.production

echo ""
echo "🧹 Cleaning up repository..."

# Cleanup reflog and gc
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "==================================================================="
echo "✅ CLEANUP COMPLETE"
echo "==================================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. VERIFY changes:"
echo "   git log --all --oneline -- .env.production"
echo "   (should return empty - file removed from history)"
echo ""
echo "2. ROTATE credentials immediately:"
echo "   See docs/CREDENTIAL_ROTATION_ESC001.md"
echo ""
echo "3. FORCE PUSH (after rotation):"
echo "   git push origin --force --all"
echo "   git push origin --force --tags"
echo ""
echo "4. NOTIFY team members:"
echo "   - All must re-clone repository OR"
echo "   - Rebase their branches on new main"
echo ""
echo "5. VERIFY on GitHub/remote:"
echo "   - Check that .env.production is not in history"
echo "   - File should only exist in .gitignore"
echo ""
echo "==================================================================="
echo ""
echo "Backup location: $BACKUP_FILE"
echo "To restore backup: git clone $BACKUP_FILE restored-repo"
echo ""
