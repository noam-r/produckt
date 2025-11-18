# ProDuckt Brand Website

This directory contains the static website for ProDuckt - an AI-powered MRD orchestration platform.

## Structure

```
docs/
├── index.html          # Main HTML file
├── css/
│   ├── main.css        # Main styles with design system
│   └── responsive.css  # Responsive breakpoints
├── js/
│   ├── main.js         # Main JavaScript functionality
│   └── smooth-scroll.js # Smooth scrolling enhancement
├── images/
│   ├── logo.svg        # ProDuckt logo
│   ├── hero-illustration.svg # Hero section illustration
│   ├── icons/          # Feature icons
│   └── screenshots/    # Product screenshots
└── README.md           # This file
```

## Features

- **Responsive Design**: Mobile-first approach with breakpoints for all devices
- **Accessibility**: WCAG 2.1 AA compliant with ARIA labels and keyboard navigation
- **Performance**: Optimized images, minimal dependencies, fast load times
- **SEO**: Semantic HTML, meta tags, Open Graph support
- **Modern CSS**: CSS variables, Grid, Flexbox
- **Vanilla JavaScript**: No framework dependencies

## Setup

### Local Development

Simply open `index.html` in a web browser, or use a local server:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx http-server

# Using PHP
php -S localhost:8000
```

Then visit `http://localhost:8000`

### Required Assets

Before deploying, you need to add the following image assets:

#### Logo
- `images/logo.svg` - ProDuckt logo (SVG format recommended)

#### Hero Section
- `images/hero-illustration.svg` - Hero section illustration

#### Feature Icons (64x64px, SVG preferred)
- `images/icons/distributed-intelligence.svg`
- `images/icons/ai-editor.svg`
- `images/icons/scoring.svg`
- `images/icons/questions.svg`
- `images/icons/collaboration.svg`
- `images/icons/professional.svg`

#### Screenshots (1200x800px recommended)
- `images/screenshots/dashboard.jpg` - Initiative overview
- `images/screenshots/context.jpg` - Company context setting
- `images/screenshots/questions.jpg` - AI-generated questions
- `images/screenshots/evaluation.jpg` - Initiative evaluation
- `images/screenshots/mrd.jpg` - Generated MRD document
- `images/screenshots/scores.jpg` - RICE and FDV scoring

#### Favicons
- `favicon.ico`
- `apple-touch-icon.png` (180x180px)
- `favicon-32x32.png`
- `favicon-16x16.png`

#### Social Media
- `images/og-image.jpg` (1200x630px for Open Graph)

## Deployment

### GitHub Pages

1. Push the `docs` folder to your repository
2. Go to Settings > Pages
3. Select "Deploy from a branch"
4. Choose `main` branch and `/docs` folder
5. Save

### Netlify

1. Connect your repository
2. Set build command: (none)
3. Set publish directory: `docs`
4. Deploy

### Vercel

1. Import your repository
2. Set output directory: `docs`
3. Deploy

### Custom Server

Upload the contents of the `docs` folder to your web server's public directory.

## Customization

### Colors

Edit CSS variables in `css/main.css`:

```css
:root {
  --primary-color: #2563eb;
  --secondary-color: #10b981;
  --accent-color: #f59e0b;
  /* ... */
}
```

### Content

Edit `index.html` to update:
- Hero section text
- Feature descriptions
- How It Works steps
- Footer information
- Contact email

### Fonts

The site uses Inter font from Google Fonts. To change:

1. Update the Google Fonts link in `index.html`
2. Update `--font-primary` in `css/main.css`

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- iOS Safari (last 2 versions)
- Android Chrome (last 2 versions)

## Performance

- Lighthouse Score Target: 90+
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.5s
- Cumulative Layout Shift: < 0.1

## Accessibility

- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader optimized
- Focus indicators
- Skip links
- ARIA labels

## License

Copyright © 2025 ProDuckt. All rights reserved.

## Contact

For questions or support: produckt.team@pm.me
