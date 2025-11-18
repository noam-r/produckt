# ProDuckt Website - Deployment Guide

This guide covers deploying the ProDuckt brand website to GitHub Pages and other hosting platforms.

## Table of Contents

1. [GitHub Pages Deployment](#github-pages-deployment)
2. [Custom Domain Setup](#custom-domain-setup)
3. [Alternative Hosting](#alternative-hosting)
4. [Post-Deployment](#post-deployment)
5. [Troubleshooting](#troubleshooting)

---

## GitHub Pages Deployment

### Automatic Deployment (Recommended)

The repository includes a GitHub Actions workflow that automatically deploys to GitHub Pages when changes are pushed to the `main` branch.

#### Setup Steps:

1. **Enable GitHub Pages in Repository Settings**
   - Go to your repository on GitHub
   - Navigate to `Settings` > `Pages`
   - Under "Build and deployment":
     - Source: Select "GitHub Actions"
   - Save the settings

2. **Push Your Code**
   ```bash
   git add .
   git commit -m "Add ProDuckt website"
   git push origin main
   ```

3. **Monitor Deployment**
   - Go to the `Actions` tab in your repository
   - Watch the "Deploy ProDuckt Website to GitHub Pages" workflow
   - Once complete, your site will be live at: `https://<username>.github.io/<repository>/`

### Manual Deployment

If you prefer manual deployment:

1. **Enable GitHub Pages**
   - Go to `Settings` > `Pages`
   - Source: Select "Deploy from a branch"
   - Branch: Select `main` and `/docs` folder
   - Save

2. **Your site will be available at:**
   - `https://<username>.github.io/<repository>/`

---

## Custom Domain Setup

### Prerequisites
- A registered domain name
- Access to your domain's DNS settings

### Steps:

1. **Add CNAME File**
   - Edit `docs/CNAME` file
   - Add your domain (e.g., `produckt.com` or `www.produckt.com`)
   - Commit and push

2. **Configure DNS Records**

   **Option A: Apex Domain (produckt.com)**
   
   Add these A records to your DNS:
   ```
   185.199.108.153
   185.199.109.153
   185.199.110.153
   185.199.111.153
   ```

   **Option B: Subdomain (www.produckt.com)**
   
   Add a CNAME record:
   ```
   CNAME: www -> <username>.github.io
   ```

3. **Enable HTTPS in GitHub**
   - Go to `Settings` > `Pages`
   - Check "Enforce HTTPS"
   - Wait for SSL certificate to provision (can take up to 24 hours)

4. **Verify**
   - Visit your custom domain
   - Ensure HTTPS is working

### DNS Propagation

DNS changes can take 24-48 hours to propagate globally. Use these tools to check:
- https://www.whatsmydns.net/
- https://dnschecker.org/

---

## Alternative Hosting

### Netlify

1. **Connect Repository**
   - Sign up at https://netlify.com
   - Click "Add new site" > "Import an existing project"
   - Connect your GitHub repository

2. **Configure Build Settings**
   - Build command: (leave empty)
   - Publish directory: `docs`
   - Click "Deploy site"

3. **Custom Domain**
   - Go to "Domain settings"
   - Add your custom domain
   - Follow Netlify's DNS instructions

### Vercel

1. **Import Project**
   - Sign up at https://vercel.com
   - Click "Add New" > "Project"
   - Import your GitHub repository

2. **Configure**
   - Framework Preset: Other
   - Root Directory: `docs`
   - Click "Deploy"

3. **Custom Domain**
   - Go to project settings > "Domains"
   - Add your domain and follow instructions

### AWS S3 + CloudFront

1. **Create S3 Bucket**
   ```bash
   aws s3 mb s3://produckt-website
   aws s3 website s3://produckt-website --index-document index.html
   ```

2. **Upload Files**
   ```bash
   aws s3 sync docs/ s3://produckt-website --delete
   ```

3. **Configure CloudFront**
   - Create CloudFront distribution
   - Origin: Your S3 bucket
   - Enable HTTPS
   - Add custom domain (CNAME)

4. **Set Bucket Policy**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Sid": "PublicReadGetObject",
       "Effect": "Allow",
       "Principal": "*",
       "Action": "s3:GetObject",
       "Resource": "arn:aws:s3:::produckt-website/*"
     }]
   }
   ```

---

## Post-Deployment

### Verification Checklist

- [ ] Site loads correctly at the deployed URL
- [ ] All pages and sections are accessible
- [ ] Images load properly
- [ ] Navigation works (including mobile menu)
- [ ] Smooth scrolling functions
- [ ] Screenshot lightbox works
- [ ] All links are functional
- [ ] HTTPS is enabled and working
- [ ] Custom domain resolves correctly (if applicable)

### SEO Setup

1. **Submit Sitemap to Search Engines**
   
   **Google Search Console:**
   - Go to https://search.google.com/search-console
   - Add your property
   - Submit sitemap: `https://yourdomain.com/sitemap.xml`

   **Bing Webmaster Tools:**
   - Go to https://www.bing.com/webmasters
   - Add your site
   - Submit sitemap

2. **Verify robots.txt**
   - Visit: `https://yourdomain.com/robots.txt`
   - Ensure it's accessible

3. **Test Open Graph Tags**
   - Use: https://developers.facebook.com/tools/debug/
   - Enter your URL and verify preview

### Performance Testing

Run these tests to ensure optimal performance:

1. **Lighthouse Audit**
   - Open Chrome DevTools
   - Go to "Lighthouse" tab
   - Run audit
   - Target: 90+ score in all categories

2. **PageSpeed Insights**
   - Visit: https://pagespeed.web.dev/
   - Test your URL
   - Address any issues

3. **GTmetrix**
   - Visit: https://gtmetrix.com/
   - Test your URL
   - Review recommendations

---

## Troubleshooting

### Site Not Loading

**Problem:** 404 error after deployment

**Solutions:**
- Verify GitHub Pages is enabled in settings
- Check that `/docs` folder is selected as source
- Ensure `index.html` exists in `/docs` folder
- Wait 5-10 minutes for initial deployment
- Check Actions tab for deployment errors

### Images Not Displaying

**Problem:** Broken image links

**Solutions:**
- Verify image paths are relative (not absolute)
- Check image files exist in `/docs/images/`
- Ensure file names match exactly (case-sensitive)
- Clear browser cache

### Custom Domain Not Working

**Problem:** Domain doesn't resolve to site

**Solutions:**
- Verify CNAME file contains correct domain
- Check DNS records are configured correctly
- Wait for DNS propagation (24-48 hours)
- Use `dig` or `nslookup` to verify DNS:
  ```bash
  dig yourdomain.com
  nslookup yourdomain.com
  ```

### HTTPS Not Working

**Problem:** SSL certificate errors

**Solutions:**
- Wait 24 hours for certificate provisioning
- Ensure "Enforce HTTPS" is checked in settings
- Verify DNS is properly configured
- Try removing and re-adding custom domain

### GitHub Actions Failing

**Problem:** Deployment workflow fails

**Solutions:**
- Check Actions tab for error messages
- Verify workflow file syntax
- Ensure Pages permissions are enabled:
  - Settings > Actions > General
  - Workflow permissions: Read and write
- Check if Pages is enabled in repository settings

### Mobile Menu Not Working

**Problem:** Hamburger menu doesn't open

**Solutions:**
- Check browser console for JavaScript errors
- Verify `main.js` is loading correctly
- Clear browser cache
- Test in different browsers

---

## Updating the Site

### Content Updates

1. Edit files in `/docs` folder
2. Commit and push changes:
   ```bash
   git add docs/
   git commit -m "Update website content"
   git push origin main
   ```
3. GitHub Actions will automatically deploy

### Adding Screenshots

1. Add images to `/docs/images/screenshots/`
2. Update `index.html` if needed
3. Commit and push

### Changing Styles

1. Edit `/docs/css/main.css` or `/docs/css/responsive.css`
2. Test locally
3. Commit and push

---

## Monitoring

### Analytics Setup (Optional)

**Google Analytics:**

Add to `<head>` in `index.html`:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

**Plausible Analytics (Privacy-friendly):**

Add to `<head>` in `index.html`:
```html
<script defer data-domain="yourdomain.com" src="https://plausible.io/js/script.js"></script>
```

---

## Support

For issues or questions:
- Email: produckt.team@pm.me
- Check GitHub Issues
- Review documentation in `/docs/README.md`

---

## Additional Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Custom Domain Setup](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)
- [Netlify Documentation](https://docs.netlify.com/)
- [Vercel Documentation](https://vercel.com/docs)
