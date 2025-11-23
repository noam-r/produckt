# CI/CD Integration Guide

This guide explains the CI/CD setup for ProDuckt's Docker-based deployment.

## Overview

The CI/CD pipeline automatically builds, tests, and publishes Docker images for ProDuckt using GitHub Actions.

## Files Created

1. **`.github/workflows/docker-build.yml`** - Main CI/CD workflow
2. **`.github/DOCKER_REGISTRY.md`** - Docker image tagging strategy documentation
3. **`docker-compose.override.yml.example`** - Template for local customizations
4. **`.gitignore`** - Updated to ignore `docker-compose.override.yml`

## Workflow Triggers

The Docker build workflow runs on:

- **Push to main/develop branches** - Builds, tests, and publishes images
- **Pull requests to main/develop** - Builds and tests only (no publish)
- **Manual trigger** - Via GitHub Actions UI (workflow_dispatch)

## What the Workflow Does

### 1. Build Phase
- Sets up Docker Buildx for advanced build features
- Builds backend and frontend images
- Uses GitHub Actions cache to speed up builds
- Loads images for testing

### 2. Test Phase
- Creates test environment configuration
- Starts all services with docker-compose
- Waits for services to become healthy
- Runs backend pytest suite
- Checks health endpoints
- Verifies frontend accessibility

### 3. Publish Phase (main/develop only)
- Builds production-optimized images
- Tags images according to strategy (see DOCKER_REGISTRY.md)
- Pushes images to GitHub Container Registry (ghcr.io)

## Image Tagging Strategy

Images are automatically tagged with:

- **Branch name** - `main`, `develop`
- **Commit SHA** - `main-abc1234`
- **Semantic version** - `1.2.3`, `1.2`, `1` (when git tag is pushed)
- **Latest** - Points to most recent main branch build

See `.github/DOCKER_REGISTRY.md` for complete details.

## Using Published Images

### Pull from Registry

```bash
# Authenticate to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull latest image
docker pull ghcr.io/your-org/produck-backend:latest
docker pull ghcr.io/your-org/produck-frontend:latest

# Pull specific version
docker pull ghcr.io/your-org/produck-backend:1.2.3
```

### Use in docker-compose

```yaml
services:
  backend:
    image: ghcr.io/your-org/produck-backend:1.2.3
    # Remove 'build' section to use pre-built image
  
  frontend:
    image: ghcr.io/your-org/produck-frontend:1.2.3
    # Remove 'build' section to use pre-built image
```

## Local Customization

### docker-compose.override.yml

Use this file for local development customizations:

```bash
# Create from template
cp docker-compose.override.yml.example docker-compose.override.yml

# Edit with your preferences
nano docker-compose.override.yml

# Docker Compose automatically applies it
docker-compose up
```

**Common customizations:**
- Change ports to avoid conflicts
- Add debug logging
- Mount additional volumes
- Add development tools (adminer, mailhog, etc.)
- Use external databases
- Adjust resource limits

**This file is gitignored** - your local changes won't be committed.

## Creating a Release

To create a new versioned release:

```bash
# 1. Ensure main branch is ready
git checkout main
git pull

# 2. Create and push a version tag
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3

# 3. GitHub Actions automatically:
#    - Builds production images
#    - Tags with 1.2.3, 1.2, 1, and latest
#    - Pushes to container registry

# 4. Deploy the release
docker pull ghcr.io/your-org/produck-backend:1.2.3
docker pull ghcr.io/your-org/produck-frontend:1.2.3
```

## Monitoring Builds

### View Workflow Runs

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Select "Docker Build and Test" workflow
4. View recent runs and their status

### Check Build Logs

1. Click on a workflow run
2. Click on the "build-and-test" job
3. Expand steps to view detailed logs

### Common Build Issues

**Build fails on tests:**
- Check test logs in the workflow output
- Run tests locally: `docker-compose exec backend pytest`
- Ensure all tests pass before pushing

**Build fails on health checks:**
- Check if services start correctly locally
- Verify environment variables are set
- Check health endpoint: `curl http://localhost:8000/health`

**Image push fails:**
- Verify GitHub token has package write permissions
- Check repository settings > Actions > General > Workflow permissions
- Ensure "Read and write permissions" is enabled

## Cache Management

The workflow uses GitHub Actions cache to speed up builds:

- **Cache scope:** Separate for backend and frontend
- **Cache type:** GitHub Actions cache (gha)
- **Cache mode:** max (caches all layers)

### Clear Cache

If builds are failing due to cache issues:

1. Go to repository Settings > Actions > Caches
2. Delete relevant caches
3. Re-run the workflow

Or use GitHub CLI:

```bash
# List caches
gh cache list

# Delete a cache
gh cache delete <cache-id>
```

## Security Considerations

### Secrets Management

The workflow uses these secrets:

- **GITHUB_TOKEN** - Automatically provided by GitHub Actions
  - Used for: Pushing images to ghcr.io
  - Permissions: Read contents, write packages

**Never commit secrets to the repository!**

For additional secrets (e.g., deployment keys):

1. Go to repository Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Add secret name and value
4. Reference in workflow: `${{ secrets.SECRET_NAME }}`

### Image Scanning

Consider adding security scanning to the workflow:

```yaml
- name: Scan backend image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: produck-backend:test
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload scan results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

## Performance Optimization

### Build Time

Current optimizations:
- ✓ Docker layer caching via GitHub Actions cache
- ✓ Multi-stage builds to separate build and runtime
- ✓ Parallel builds for backend and frontend
- ✓ Buildx for advanced build features

Typical build times:
- **First build:** 5-8 minutes
- **Cached build:** 2-3 minutes
- **No changes:** 30-60 seconds

### Cache Hit Rate

Monitor cache effectiveness:
- Check workflow logs for "cache hit" messages
- If cache hit rate is low, review Dockerfile layer ordering
- Place frequently changing files (source code) last

## Troubleshooting

### Workflow fails on "Wait for services"

**Cause:** Services not becoming healthy in time

**Solutions:**
1. Increase timeout in workflow (currently 120s for backend)
2. Check if services start locally: `docker-compose up`
3. Review service logs in workflow output

### Tests pass locally but fail in CI

**Cause:** Environment differences

**Solutions:**
1. Check environment variables in workflow
2. Ensure test database is isolated
3. Check for timing issues (add retries/waits)
4. Run tests in CI environment locally:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   docker-compose exec backend pytest
   ```

### Images not appearing in registry

**Cause:** Workflow doesn't push on PRs, or permissions issue

**Solutions:**
1. Verify workflow ran on main/develop branch (not PR)
2. Check workflow permissions in repository settings
3. Verify GITHUB_TOKEN has package write access
4. Check workflow logs for push step errors

### docker-compose.override.yml conflicts

**Cause:** Override file conflicts with main configuration

**Solutions:**
1. Review override file syntax
2. Test with: `docker-compose config` (shows merged config)
3. Temporarily rename override file to debug
4. Check for duplicate keys or invalid YAML

## Best Practices

1. **Always test locally before pushing**
   ```bash
   docker-compose build
   docker-compose up -d
   docker-compose exec backend pytest
   ```

2. **Use semantic versioning for releases**
   - Major: Breaking changes (v2.0.0)
   - Minor: New features (v1.1.0)
   - Patch: Bug fixes (v1.0.1)

3. **Pin production images to specific versions**
   ```yaml
   # Good
   image: ghcr.io/org/produck-backend:1.2.3
   
   # Avoid in production
   image: ghcr.io/org/produck-backend:latest
   ```

4. **Keep docker-compose.override.yml local**
   - Never commit this file
   - Document common overrides in the example file
   - Share team-specific overrides via documentation

5. **Monitor build times and cache hit rates**
   - Optimize Dockerfile layer ordering
   - Review dependencies regularly
   - Clean up unused images and caches

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Compose Override](https://docs.docker.com/compose/extends/)

## Getting Help

- **Workflow issues:** Check GitHub Actions logs
- **Docker issues:** See [DOCKER.md](../DOCKER.md)
- **General issues:** [GitHub Issues](https://github.com/noam-r/produckt/issues)
