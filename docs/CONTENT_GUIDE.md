# ProDuckt Website - Content Update Guide

This guide explains how to update content on the ProDuckt website without technical knowledge.

## Quick Reference

- **Hero Section**: Edit `index.html` lines 60-85
- **Features**: Edit `index.html` lines 90-150
- **How It Works**: Edit `index.html` lines 155-200
- **Screenshots**: Replace files in `/docs/images/screenshots/`
- **Footer**: Edit `index.html` lines 250-280

## Updating Text Content

### Hero Section

**Location:** `docs/index.html` (lines 60-85)

**What to change:**
- Main headline
- Subheadline
- Tagline
- Button text

**Example:**
```html
<h1 class="hero-title">Your New Headline Here</h1>
<p class="hero-subtitle">Your new description here</p>
```

### Features Section

**Location:** `docs/index.html` (lines 90-150)

**Each feature has:**
- Icon (SVG file)
- Title (h3)
- Description (p)

**To update a feature:**
1. Find the feature card
2. Update the `<h3>` for the title
3. Update the `<p>` for the description

### How It Works Steps

**Location:** `docs/index.html` (lines 155-200)

**Each step has:**
- Number (automatically styled)
- Title (h3)
- Description (p)

**To update:**
```html
<h3>Your Step Title</h3>
<p>Your step description</p>
```

## Updating Images

### Screenshots

**Location:** `/docs/images/screenshots/`

**Required dimensions:** 1200x800px (or 3:2 ratio)

**File names:**
- `dashboard.jpg`
- `context.jpg`
- `questions.jpg`
- `evaluation.jpg`
- `mrd.jpg`
- `scores.jpg`

**Steps:**
1. Prepare your image (1200x800px)
2. Save as JPG (optimized, < 200KB)
3. Replace the file in `/docs/images/screenshots/`
4. Keep the same filename
5. Commit and push changes

### Logo

**Location:** `/docs/images/logo.svg`

**Format:** SVG (recommended) or PNG

**Dimensions:** 160x40px (or similar ratio)

**To replace:**
1. Create your logo
2. Save as `logo.svg`
3. Replace `/docs/images/logo.svg`


### Feature Icons

**Location:** `/docs/images/icons/`

**Format:** SVG (32x32px)

**Files:**
- `distributed-intelligence.svg`
- `ai-editor.svg`
- `scoring.svg`
- `questions.svg`
- `collaboration.svg`
- `professional.svg`

**To replace:**
1. Create icon as SVG (32x32px)
2. Use white color for icon elements
3. Replace the corresponding file
4. Keep the same filename

## Updating Colors

**Location:** `docs/css/main.css` (lines 1-50)

**Primary colors:**
```css
--primary-color: #2563eb;    /* Main brand color */
--secondary-color: #10b981;  /* Accent color */
--accent-color: #f59e0b;     /* Highlight color */
```

**To change:**
1. Open `docs/css/main.css`
2. Find the `:root` section
3. Update the color values (use hex codes)
4. Save and test

## Updating Contact Information

**Email:** Search for `produckt.team@pm.me` in `index.html` and replace

**Footer links:**
- Location: `docs/index.html` (lines 250-280)
- Update href attributes and link text

## Testing Changes Locally

Before deploying, test your changes:

1. **Open in browser:**
   - Navigate to `/docs/` folder
   - Double-click `index.html`
   - Or use a local server

2. **Using Python:**
   ```bash
   cd docs
   python -m http.server 8000
   ```
   Visit: http://localhost:8000

3. **Using Node.js:**
   ```bash
   cd docs
   npx http-server
   ```

## Deploying Changes

After making changes:

```bash
git add docs/
git commit -m "Update website content"
git push origin main
```

GitHub Actions will automatically deploy your changes.

## Common Tasks

### Adding a New Feature

1. Copy an existing feature card in `index.html`
2. Update the icon, title, and description
3. Create a new icon SVG if needed
4. Save and deploy

### Changing Button Text

Search for `btn` class in `index.html`:
```html
<a href="#cta" class="btn btn-primary">Your Button Text</a>
```

### Updating Meta Description (SEO)

Find this line in `index.html`:
```html
<meta name="description" content="Your new description">
```

### Changing Page Title

Find this line in `index.html`:
```html
<title>Your New Page Title</title>
```

## Image Optimization

Before uploading images:

1. **Resize to correct dimensions**
2. **Compress:**
   - Use https://tinypng.com/
   - Or https://squoosh.app/
3. **Target file size:**
   - Screenshots: < 200KB each
   - Icons: < 10KB each
   - Logo: < 20KB

## Troubleshooting

### Changes Not Showing

1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
2. Wait 2-3 minutes for deployment
3. Check GitHub Actions for errors

### Broken Layout

1. Verify HTML tags are properly closed
2. Check for missing quotes in attributes
3. Validate HTML: https://validator.w3.org/

### Images Not Loading

1. Check file path is correct
2. Verify filename matches exactly (case-sensitive)
3. Ensure image file exists in correct folder

## Best Practices

- **Always test locally before deploying**
- **Keep backups of original files**
- **Use descriptive commit messages**
- **Optimize images before uploading**
- **Maintain consistent formatting**
- **Test on mobile devices**

## Need Help?

Contact: produckt.team@pm.me
