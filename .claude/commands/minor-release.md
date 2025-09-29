# Minor Release

Create a minor release (increment second version number, e.g., 0.2.4 → 0.3.0).

## Steps

1. **Determine current version**:
   - Read `custom_components/compool/manifest.json` to get current version
   - Calculate new minor version by incrementing the minor number and resetting patch to 0

2. **Update version files**:
   - Update `custom_components/compool/manifest.json` version field
   - Update CHANGELOG.md:
     - Move [Unreleased] section to new version with current date
     - Create new empty [Unreleased] section at top
     - Use format: `## [X.Y.0] - YYYY-MM-DD`

3. **Run quality checks**:
   - Run `scripts/test` to ensure all tests pass
   - Run `scripts/lint` to ensure code quality
   - If either fails, stop and report errors

4. **Commit and tag**:
   - Commit changes with message: "Release vX.Y.0"
   - Create git tag: `git tag vX.Y.0`
   - Push commit: `git push`
   - Push tag: `git push origin vX.Y.0`

5. **Create GitHub release**:
   - Use `gh release create vX.Y.0 --title "vX.Y.0" --notes-file CHANGELOG_EXCERPT.md`
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

- Minor releases are for new features and enhancements
- Backward compatibility must be maintained
- Breaking changes are not allowed in minor releases
- New sensors, services, or platforms can be added