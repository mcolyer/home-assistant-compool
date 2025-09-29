# Patch Release

Create a patch release (increment third version number, e.g., 0.2.4 → 0.2.5).

## Steps

1. **Determine current version**:
   - Read `custom_components/compool/manifest.json` to get current version
   - Calculate new patch version by incrementing the patch number

2. **Update version files**:
   - Update `custom_components/compool/manifest.json` version field
   - Update CHANGELOG.md:
     - Move [Unreleased] section to new version with current date
     - Create new empty [Unreleased] section at top
     - Use format: `## [X.Y.Z] - YYYY-MM-DD`

3. **Run quality checks**:
   - Run `scripts/test` to ensure all tests pass
   - Run `scripts/lint` to ensure code quality
   - If either fails, stop and report errors

4. **Commit and tag**:
   - Commit changes with message: "Release vX.Y.Z"
   - Create git tag: `git tag vX.Y.Z`
   - Push commit: `git push`
   - Push tag: `git push origin vX.Y.Z`

5. **Create GitHub release**:
   - Use `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file CHANGELOG_EXCERPT.md`
   - Extract release notes from CHANGELOG.md for the new version
   - Add standard footer:
     ```
     ---
     🤖 Generated with [Claude Code](https://claude.com/claude-code)
     ```

6. **Report completion**:
   - Display new version number
   - Show GitHub release URL
   - Remind to verify release on GitHub

## Notes

- Patch releases are for bug fixes and small updates
- Do not add new features in patch releases
- Breaking changes are never allowed in patch releases