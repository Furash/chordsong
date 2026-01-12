#!/usr/bin/env python3
"""
Release helper script to bump version in blender_manifest.toml and optionally create a git tag.

This script is used for preparing releases. It updates the version in the manifest file
and can optionally create and push git tags to trigger the GitHub Actions release workflow.

Usage:
    python .github/scripts/bump_version.py 1.0.5                            # Update version only
    python .github/scripts/bump_version.py 1.0.5 --commit                   # Update version + commit blender_manifest.toml
    python .github/scripts/bump_version.py 1.0.5 --tag                      # Update version and create tag v1.0.5
    python .github/scripts/bump_version.py 1.0.5 --commit --tag             # Commit first, then tag the commit
    python .github/scripts/bump_version.py 1.0.5 --commit --tag --push      # Commit, tag, and push commit+tag
"""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false

import argparse
import sys
import os
import subprocess

try:
    import tomli
    import tomli_w
except ImportError:
    print("Error: tomli and tomli-w are required. Install with: pip install tomli tomli-w")
    sys.exit(1)


def update_manifest_version(version: str) -> bool:
    """Update version in blender_manifest.toml."""
    manifest_path = "blender_manifest.toml"
    
    if not os.path.exists(manifest_path):
        print(f"Error: {manifest_path} not found")
        return False
    
    try:
        # Read manifest
        with open(manifest_path, 'rb') as f:
            manifest = tomli.load(f)
        
        old_version = manifest.get('version', 'unknown')
        manifest['version'] = version
        
        # Write back
        with open(manifest_path, 'wb') as f:
            tomli_w.dump(manifest, f)
        
        print(f"✅ Updated version from {old_version} to {version} in {manifest_path}")
        return True
    except (OSError, tomli.TOMLDecodeError) as e:
        print(f"Error updating manifest: {e}")
        return False


def _run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def _git_stdout(args: list[str]) -> str:
    return _run_git(args, check=False).stdout.strip()


def commit_manifest_version(version: str, *, message: str | None = None) -> bool:
    """Stage & commit blender_manifest.toml so the repo reflects the bumped version."""
    if message is None:
        message = f"Bump version to {version}"

    try:
        # Ensure we're in a git repo
        if not _git_stdout(["rev-parse", "--is-inside-work-tree"]) == "true":
            print("Error: not inside a git work tree")
            return False

        # Stage manifest
        _run_git(["add", "blender_manifest.toml"], check=True)

        # If nothing changed, don't create an empty commit
        status = _git_stdout(["status", "--porcelain", "--", "blender_manifest.toml"])
        if not status:
            print("ℹ️  blender_manifest.toml unchanged; skipping commit")
            return True

        _run_git(["commit", "-m", message], check=True)
        print(f"✅ Committed blender_manifest.toml ({message})")
        return True
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        print(f"Error committing manifest: {stderr or e}")
        return False


def create_tag(version: str, push: bool = False) -> bool:
    """Create a git tag for the version."""
    tag_name = f"v{version}"
    
    try:
        # Check if tag already exists
        result = subprocess.run(
            ['git', 'tag', '-l', tag_name],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout.strip():
            print(f"⚠️  Tag {tag_name} already exists")
            response = input("   Do you want to delete and recreate it? (y/N): ")
            if response.lower() == 'y':
                subprocess.run(['git', 'tag', '-d', tag_name], check=False)
                if push:
                    subprocess.run(['git', 'push', 'origin', '--delete', tag_name], check=False)
            else:
                return False
        
        # Create tag
        subprocess.run(['git', 'tag', tag_name], check=True)
        print(f"✅ Created tag: {tag_name}")
        
        if push:
            subprocess.run(['git', 'push', 'origin', tag_name], check=True)
            print(f"✅ Pushed tag: {tag_name}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating tag: {e}")
        return False
    except KeyboardInterrupt:
        print("\nCancelled")
        return False


def push_tag(version: str) -> bool:
    """Push an already-created local tag to origin."""
    tag_name = f"v{version}"
    try:
        _run_git(["push", "origin", tag_name], check=True)
        print(f"✅ Pushed tag: {tag_name}")
        return True
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        print(f"Error pushing tag: {stderr or e}")
        return False


def push_current_branch() -> bool:
    """Push current branch to origin (needed to update repo files on GitHub)."""
    try:
        branch = _git_stdout(["rev-parse", "--abbrev-ref", "HEAD"])
        if not branch or branch == "HEAD":
            print("Error: detached HEAD; cannot push current branch")
            return False
        _run_git(["push", "origin", branch], check=True)
        print(f"✅ Pushed branch: {branch}")
        return True
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        print(f"Error pushing branch: {stderr or e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Bump version in blender_manifest.toml and optionally create a git tag'
    )
    parser.add_argument('version', help='Version number (e.g., 1.0.5)')
    parser.add_argument('--commit', action='store_true', help='Commit blender_manifest.toml after updating version')
    parser.add_argument('--tag', action='store_true', help='Create git tag v{VERSION}')
    parser.add_argument('--push', action='store_true', help='Push commit (if --commit) and tag (if --tag) to origin')
    parser.add_argument('--message', help='Commit message (used with --commit)')
    
    args = parser.parse_args()
    
    # Validate version format (basic check)
    version_parts = args.version.split('.')
    if len(version_parts) != 3 or not all(p.isdigit() for p in version_parts):
        print("Error: Invalid version format. Expected format: X.Y.Z (e.g., 1.0.5)")
        sys.exit(1)
    
    # Update manifest
    if not update_manifest_version(args.version):
        sys.exit(1)
    
    # Commit manifest if requested (recommended when tagging)
    if args.commit:
        if not commit_manifest_version(args.version, message=args.message):
            sys.exit(1)
        if args.push and not args.tag:
            if not push_current_branch():
                sys.exit(1)

    # Create tag if requested
    if args.tag:
        # If we are pushing and tagging, ensure the manifest update is committed first,
        # otherwise GitHub will never see the updated blender_manifest.toml.
        if args.push and not args.commit:
            print("Error: --push with --tag requires --commit so the version bump reaches the remote repo.")
            print("       Use: --commit --tag --push")
            sys.exit(1)

        if not create_tag(args.version, False):
            sys.exit(1)

        if args.push:
            if not push_current_branch():
                sys.exit(1)
            if not push_tag(args.version):
                sys.exit(1)
    
    print("\n✨ Version bump complete!")
    if args.commit:
        print("   Commit: blender_manifest.toml updated")
    if args.tag:
        print(f"   Tag: v{args.version}")
    if args.push:
        print("   Pushed to remote origin")
    elif args.tag:
        print(f"   To push the tag: git push origin v{args.version}")


if __name__ == '__main__':
    main()
