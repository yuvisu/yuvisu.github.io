# yuvisu.github.io

Personal research site of Yu Huang, served by GitHub Pages from `master`.
It is a plain Jekyll site with no theme gem: content lives in `_data/`, pages
are the `.html` files at the top level, and all styling is in
`assets/css/site.css`.

## Where things are

| To change | Edit |
| --- | --- |
| Name, title, tagline, links, nav | `_config.yml` |
| Bio and the home page layout | `index.html` |
| News | `_data/news.yml` (newest first; the home page shows 6) |
| Research themes, featured projects, selected papers | `_data/research.yml` |
| Current funding | `_data/funding.yml` |
| Trainees | `_data/people.yml` |
| Positions, education, awards, talks, service | `_data/cv.yml` |
| Publications | the CV's `.bib` files, then regenerate (below) |

## Publications

The CV in `YH_KB/YUCV/bib` is the source of truth. After editing it:

```bash
python3 scripts/build_publications.py        # writes _data/publications.json
python3 scripts/find_pub_links.py            # optional: look up DOIs for new papers
python3 scripts/build_publications.py        # pick up the new links
```

- Links live in `scripts/pub_links.json` (bib key -> URL); add or fix them by hand there.
- Bib keys in `scripts/pub_hidden.json` stay in the CV but are not shown on the site.
- `@comment` entries in the bib are hidden, as they are in the CV.

## CV PDF

Put a public version of the CV at `files/Yu_Huang_CV.pdf` and a download button
appears on `/cv/`. Leave out the phone number and pending grants.

## Preview locally

GitHub Pages needs Ruby 3.x (`brew install ruby@3.3`):

```bash
export PATH=/opt/homebrew/opt/ruby@3.3/bin:$PATH LANG=en_US.UTF-8
bundle config set --local path vendor/bundle
bundle install
bundle exec jekyll serve
```

Then open http://localhost:4000.
