#!/usr/bin/env python3
"""
Release helper script to bump version in blender_manifest.toml and optionally create a git tag.

This script is used for preparing releases. It updates the version in the manifest file
and can optionally create and push git tags to trigger the GitHub Actions release workflow.

Usage:
    python .github/scripts/bump_version.py 1.0.5              # Update version only
    python .github/scripts/bump_version.py 1.0.5 --tag        # Update version and create tag v1.0.5
    python .github/scripts/bump_version.py 1.0.5 --tag --push  # Update version, create tag, and push
"""

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
    except Exception as e:
        print(f"Error updating manifest: {e}")
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
            response = input(f"   Do you want to delete and recreate it? (y/N): ")
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


def main():
    parser = argparse.ArgumentParser(
        description='Bump version in blender_manifest.toml and optionally create a git tag'
    )
    parser.add_argument('version', help='Version number (e.g., 1.0.5)')
    parser.add_argument('--tag', action='store_true', help='Create git tag v{VERSION}')
    parser.add_argument('--push', action='store_true', help='Push tag to remote (requires --tag)')
    
    args = parser.parse_args()
    
    # Validate version format (basic check)
    version_parts = args.version.split('.')
    if len(version_parts) != 3 or not all(p.isdigit() for p in version_parts):
        print(f"Error: Invalid version format. Expected format: X.Y.Z (e.g., 1.0.5)")
        sys.exit(1)
    
    # Update manifest
    if not update_manifest_version(args.version):
        sys.exit(1)
    
    # Create tag if requested
    if args.tag:
        if not create_tag(args.version, args.push):
            sys.exit(1)
    
    print(f"\n✨ Version bump complete!")
    if args.tag:
        print(f"   Tag: v{args.version}")
        if args.push:
            print(f"   Tag pushed to remote")
        else:
            print(f"   To push the tag: git push origin v{args.version}")


if __name__ == '__main__':
    main()
