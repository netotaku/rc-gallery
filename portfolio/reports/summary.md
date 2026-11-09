# Redcatch asset review report

115 JPEGs were inventoried. Every original still matches its initial SHA-256 hash. Every source image is accounted for. Videos in mp4 were left untouched and outside this phase.

- 114 unique file contents; 1 redundant exact copy.
- 13 near-duplicate candidate pairs, all retained for review.
- 19 proposed project groups; 49 unassigned images.
- 68 automatic padding crop proposals pending approval.
- Project categories: {'Domestic Scaffolding': 6, 'Temporary Roofs / False Roofs': 3, 'Needs review': 10}.
- Grouping confidence: {'medium': 9, 'high': 10}.
- Dimensions: 736–2000 pixels wide, 902–2048 pixels high. Seventy-three images are 736 × 1600 screenshots.

Clean masters preserve full usable resolution. Unchanged masters are source copies; transformed masters are lossless PNGs. WebP previews and thumbnails never upscale. All generated manifest paths exist. QA found no missing assets or altered originals. Automated integration checks passed for saved moves, splits, merges, hero selection, suitability, category/group approval and manual cropping, including crop bounds and local path traversal checks. JavaScript syntax was checked. A full browser interaction test was unavailable. The rerun-check.json report records the independent actual-collection idempotency check.

## Review still needed

Project proposals come from image-capable visual contact-sheet inspection, using repeated architecture, site details and scaffold configuration. No embedding model is installed; new imports stay unassigned. Some groups deliberately remain in Needs review because photographs do not establish building use. Titles describe visible work provisionally. Client identity, location, dates and service scope remain unverified.

Inspect each crop at full size before approving. Uniform black padding is detected conservatively; toolbars, home indicators and unusually large borders may need manual coordinates. Physically sideways source images require rotation in a separate copy or a future rotation control. Contact-sheet review supports proposals but cannot guarantee that every crop preserves every meaningful detail.

Difference hashes and ORB/RANSAC feature matching identify possible screenshot/original, resized and cropped copies. Candidates may show different viewpoints or construction stages, so none is excluded automatically. Exact duplicates use complete-file SHA-256. All original versions remain retained. Prefer the best usable resolution after inspecting quality and framing.

Use the local interface to confirm groups and crops, choose primary categories and secondary service tags, and select preferred images. Ready status means ready for preliminary content development, not publication. No website pages or finished SEO case studies have been created.

See README.md for operation, repeat processing, format support, dependencies and colour-profile limitations.
