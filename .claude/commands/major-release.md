# Major Release

Create a major release (increment first version number, e.g., 0.2.4 → 1.0.0).

## Steps

1. **Determine current version**:
   - Read `custom_components/compool/manifest.json` to get current version
   - Calculate new major version by incrementing the major number and resetting minor and patch to 0

2. **Update version files**:
   - Update `custom_components/compool/manifest.json` version field
   - Update CHANGELOG.md:
     - Move [Unreleased] section to new version with current date
     - Create new empty [Unreleased] section at top
     - Use format: `## [X.0.0] - YYYY-MM-DD`

3. **Run quality checks**:
   - Run `scripts/test` to ensure all tests pass
   - Run `scripts/lint` to ensure code quality
   - If either fails, stop and report errors

4. **Commit and tag**:
   - Commit changes with message: "Release vX.0.0"
   - Create git tag: `git tag vX.0.0`
   - Push commit: `git push`
   - Push tag: `git push origin vX.0.0`

5. **Create GitHub release**:
   - Use `gh release create vX.0.0 --title "vX.0.0" --notes-file CHANGELOG_EXCERPT.md`
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

- Major releases are for breaking changes
- May include incompatible API changes
- May remove deprecated features
- Require careful migration documentation
- Users may need to update their configurations
- Consider adding migration guide in release notes