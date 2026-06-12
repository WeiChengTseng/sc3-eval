# Paper Website Template

This repository contains a simple static project page for an anonymous paper submission.
It uses plain HTML and CSS, so there is no build step or package installation.

## Edit The Content

- Update `index.html` with the paper title, venue, abstract, and appendix link.
- Replace the placeholder figure blocks with images or videos from the `assets/` directory.
- Put your appendix PDF at `assets/appendix.pdf`, or update the appendix link in `index.html`.
- Keep author names, affiliations, personal contact information, and non-anonymous repository links out of the site until the review period ends.
- Adjust colors, spacing, and typography in `styles.css`.

## Preview Locally

Open `index.html` in a browser. You can also serve the folder with any static file server, for example:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Publish With GitHub Pages

1. Push this repository to GitHub.
2. Open the repository settings.
3. Go to Pages.
4. Select the main branch and the repository root as the source.
5. Save the settings and wait for GitHub to publish the site.
