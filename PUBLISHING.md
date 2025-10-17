# Publishing Dilon Claude Tools to GitHub Packages

This guide explains how to publish the `@dilon/claude-tools` package to GitHub Packages for internal distribution.

## Prerequisites

1. **GitHub Account** with access to the `dilontechnologies` organization
2. **Personal Access Token** (PAT) with `write:packages` and `read:packages` permissions
3. **npm** installed on your machine

## One-Time Setup

### 1. Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name: "NPM Package Publishing"
4. Select scopes:
   - ✅ `write:packages` (upload packages)
   - ✅ `read:packages` (download packages)
   - ✅ `repo` (for private repos, if needed)
5. Click "Generate token"
6. **Copy the token** - you won't see it again!

### 2. Configure npm Authentication

Add the token to your `.npmrc` file:

**Option A: Global configuration** (recommended for personal machines)
```bash
npm config set //npm.pkg.github.com/:_authToken YOUR_TOKEN_HERE
```

**Option B: Project-specific** (create `.npmrc` in project root)
```
//npm.pkg.github.com/:_authToken=YOUR_TOKEN_HERE
@dilontechnologies:registry=https://npm.pkg.github.com
```

⚠️ **Never commit `.npmrc` with tokens to git!** It's already in `.gitignore`.

### 3. Verify Authentication

```bash
npm whoami --registry=https://npm.pkg.github.com
```

Should show your GitHub username.

## Publishing a New Version

### 1. Update Version Number

```bash
# Bump patch version (1.0.0 → 1.0.1)
npm version patch

# Bump minor version (1.0.0 → 1.1.0)
npm version minor

# Bump major version (1.0.0 → 2.0.0)
npm version major

# Or set specific version
npm version 1.2.3
```

This automatically:
- Updates `package.json`
- Creates a git commit
- Creates a git tag

### 2. Update CHANGELOG.md

Document the changes in `CHANGELOG.md`:

```markdown
## [1.0.1] - 2025-01-20

### Fixed
- Fixed issue with PlantUML path detection

### Changed
- Updated documentation
```

### 3. Commit Changes

```bash
git add CHANGELOG.md
git commit -m "Update CHANGELOG for v1.0.1"
```

### 4. Publish to GitHub Packages

```bash
npm publish
```

This will:
- Build the package
- Upload to GitHub Packages
- Make it available at `@dilon/claude-tools@1.0.1`

### 5. Push to GitHub

```bash
git push origin main
git push --tags
```

## Installing from GitHub Packages

### For Team Members

#### First-Time Setup

1. **Create GitHub PAT** (same as above, but only needs `read:packages`)

2. **Configure npm to use GitHub Packages**:
   ```bash
   npm config set @dilontechnologies:registry https://npm.pkg.github.com
   npm config set //npm.pkg.github.com/:_authToken YOUR_TOKEN_HERE
   ```

3. **Install the package**:
   ```bash
   npm install -g @dilontechnologies/claude-tools
   ```

The postinstall script will automatically:
- Register the MCP server with Claude Desktop
- Create default configuration
- Check for dependencies

4. **Restart Claude Desktop** to load the tools

#### Updating to Latest Version

```bash
npm update -g @dilontechnologies/claude-tools
```

## Package Information

View published package:
```bash
npm view @dilontechnologies/claude-tools
```

View all versions:
```bash
npm view @dilontechnologies/claude-tools versions
```

View on GitHub:
```
https://github.com/dilontechnologies/dilon-claude-tools/packages
```

## Troubleshooting

### "404 Not Found" when publishing

**Solution**: Ensure the package name in `package.json` matches your GitHub org:
```json
{
  "name": "@dilontechnologies/claude-tools",
  "publishConfig": {
    "registry": "https://npm.pkg.github.com"
  }
}
```

### Authentication failures

**Solution**: Regenerate your token and update `.npmrc`:
```bash
npm config set //npm.pkg.github.com/:_authToken NEW_TOKEN_HERE
```

### "Package already exists" error

**Solution**: Bump the version number first:
```bash
npm version patch
npm publish
```

### Installation hangs or fails

**Solution**: Check authentication:
```bash
npm whoami --registry=https://npm.pkg.github.com
```

If it fails, recreate your `.npmrc` with a fresh token.

## Best Practices

1. **Always test locally first**:
   ```bash
   npm pack
   npm install -g ./dilon-claude-tools-1.0.0.tgz
   ```

2. **Use semantic versioning**:
   - **Patch** (1.0.x): Bug fixes
   - **Minor** (1.x.0): New features (backward compatible)
   - **Major** (x.0.0): Breaking changes

3. **Update CHANGELOG.md** before publishing

4. **Tag releases** in GitHub after publishing

5. **Document breaking changes** clearly in CHANGELOG

## Automated Publishing (Future)

Consider setting up GitHub Actions for automated publishing:

```yaml
# .github/workflows/publish.yml
name: Publish Package
on:
  release:
    types: [created]
jobs:
  publish:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://npm.pkg.github.com'
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{secrets.GITHUB_TOKEN}}
```

## Security Notes

- **Never** commit `.npmrc` with tokens
- **Never** commit Personal Access Tokens to git
- **Rotate tokens** regularly (every 6-12 months)
- Use **read-only tokens** for installation, **write tokens** only for publishing
- Store tokens in password manager or GitHub Secrets for CI/CD

---

**Internal Use Only** - Dilon Technologies LLC
