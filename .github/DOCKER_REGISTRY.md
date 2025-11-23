# Docker Image Tagging Strategy

This document describes the Docker image tagging strategy used in the ProDuckt CI/CD pipeline.

## Image Repositories

Images are published to GitHub Container Registry (ghcr.io):

- **Backend**: `ghcr.io/<owner>/produck-backend`
- **Frontend**: `ghcr.io/<owner>/produck-frontend`

## Tagging Strategy

### Automatic Tags

The CI/CD pipeline automatically generates the following tags:

#### 1. Branch-based Tags

When code is pushed to a branch:
- `main` - Latest code from the main branch
- `develop` - Latest code from the develop branch
- `<branch-name>` - Latest code from any other branch

**Example:**
```bash
docker pull ghcr.io/your-org/produck-backend:main
docker pull ghcr.io/your-org/produck-backend:develop
```

#### 2. Commit SHA Tags

Every commit gets tagged with its SHA, prefixed by the branch name:
- `main-abc1234` - Commit abc1234 from main branch
- `develop-def5678` - Commit def5678 from develop branch

**Example:**
```bash
docker pull ghcr.io/your-org/produck-backend:main-abc1234
```

**Use case:** Rollback to a specific commit or debug a specific build.

#### 3. Semantic Version Tags

When you create a git tag with semantic versioning (e.g., `v1.2.3`):
- `1.2.3` - Full version
- `1.2` - Major.minor version
- `1` - Major version only

**Example:**
```bash
# Create a release tag
git tag v1.2.3
git push origin v1.2.3

# Pull the versioned image
docker pull ghcr.io/your-org/produck-backend:1.2.3
docker pull ghcr.io/your-org/produck-backend:1.2
docker pull ghcr.io/your-org/produck-backend:1
```

#### 4. Latest Tag

The `latest` tag always points to the most recent build from the default branch (main):
- `latest` - Latest production-ready image

**Example:**
```bash
docker pull ghcr.io/your-org/produck-backend:latest
```

#### 5. Pull Request Tags

For pull requests, images are tagged with the PR number:
- `pr-123` - Build from pull request #123

**Note:** PR images are built but not pushed to the registry by default.

## Using Tagged Images

### Development

For development, use branch-based tags:

```yaml
# docker-compose.yml
services:
  backend:
    image: ghcr.io/your-org/produck-backend:develop
  frontend:
    image: ghcr.io/your-org/produck-frontend:develop
```

### Staging

For staging, use commit SHA tags for reproducibility:

```yaml
services:
  backend:
    image: ghcr.io/your-org/produck-backend:main-abc1234
  frontend:
    image: ghcr.io/your-org/produck-frontend:main-abc1234
```

### Production

For production, use semantic version tags:

```yaml
services:
  backend:
    image: ghcr.io/your-org/produck-backend:1.2.3
  frontend:
    image: ghcr.io/your-org/produck-frontend:1.2.3
```

Or use major.minor for automatic patch updates:

```yaml
services:
  backend:
    image: ghcr.io/your-org/produck-backend:1.2
  frontend:
    image: ghcr.io/your-org/produck-frontend:1.2
```

## Creating a Release

To create a new release with proper versioning:

1. **Update version in your code** (if applicable)

2. **Create and push a git tag:**
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```

3. **GitHub Actions will automatically:**
   - Build the Docker images
   - Tag them with `1.2.3`, `1.2`, `1`, and `latest`
   - Push them to the container registry

4. **Deploy the release:**
   ```bash
   docker pull ghcr.io/your-org/produck-backend:1.2.3
   docker pull ghcr.io/your-org/produck-frontend:1.2.3
   ```

## Pulling Images

### Authentication

To pull images from GitHub Container Registry, you need to authenticate:

```bash
# Using a personal access token
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Or using GitHub CLI
gh auth token | docker login ghcr.io -u USERNAME --password-stdin
```

### Pull Commands

```bash
# Pull latest from main branch
docker pull ghcr.io/your-org/produck-backend:latest

# Pull specific version
docker pull ghcr.io/your-org/produck-backend:1.2.3

# Pull specific commit
docker pull ghcr.io/your-org/produck-backend:main-abc1234

# Pull from develop branch
docker pull ghcr.io/your-org/produck-backend:develop
```

## Image Visibility

By default, images pushed to GitHub Container Registry are private. To make them public:

1. Go to the package page on GitHub
2. Click "Package settings"
3. Scroll to "Danger Zone"
4. Click "Change visibility" and select "Public"

## Cache Strategy

The CI/CD pipeline uses GitHub Actions cache to speed up builds:

- **Cache scope**: Separate caches for backend and frontend
- **Cache mode**: `max` - caches all layers
- **Cache type**: `gha` - GitHub Actions cache

This significantly reduces build times for subsequent builds.

## Troubleshooting

### Image not found

If you get "image not found" errors:

1. Check that the workflow has completed successfully
2. Verify you're authenticated to ghcr.io
3. Check the package visibility settings
4. Ensure the tag exists (check the package page on GitHub)

### Old images

To clean up old images:

1. Go to the package page on GitHub
2. Click on "Package settings"
3. Use the "Manage versions" section to delete old versions

Or use the GitHub CLI:

```bash
# List all versions
gh api /user/packages/container/produck-backend/versions

# Delete a specific version
gh api -X DELETE /user/packages/container/produck-backend/versions/VERSION_ID
```

## Best Practices

1. **Use semantic versioning** for production releases
2. **Use commit SHA tags** for staging and debugging
3. **Use branch tags** for development and testing
4. **Never use `latest` in production** - always pin to a specific version
5. **Tag releases** in git to trigger automatic versioned builds
6. **Document breaking changes** in release notes when bumping major versions
