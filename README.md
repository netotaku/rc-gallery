# Redcatch portfolio asset organiser

Start the local review application from this directory:

```sh
python3 organiser/server.py
```

Open **http://127.0.0.1:8765**. The server binds only to your computer. Stop it with Ctrl+C. The application requires Python 3.9+, NumPy and OpenCV (already available in this workspace). For another machine install `numpy` and `opencv-python`. On macOS, HEIC decoding falls back to the built-in `sips` utility; elsewhere install a compatible OpenCV decoder or convert a separate copy before import. Decode errors are recorded, never silently dropped.

## Review

The main Finalised gallery shows retained photographs in sections by project, with each project title above its thumbnail grid. Tick Hero image to choose the single lead photo for that project; choosing another replaces the previous selection and saves immediately. Unsuitable photographs appear in their own section and navigation view, with Restore returning them to their existing group. Unassigned retained photos appear separately. Use Rename group beside a section heading to open an inline name field, then click Save name (or Cancel). Renaming preserves approval and image assignments. Each thumbnail has a Move to group dropdown that saves its new assignment immediately, including an Unassigned option. Unsuitable images keep their excluded status when moved. Edit group opens the detailed review tools.

The initial groups are visual proposals, not verified site identities. Open a project to inspect its evidence, change category and service tags, select a hero, approve the grouping, or mark it ready for content development. Building use that cannot be established stays in Needs review. No names, addresses or completion dates have been inferred.

Use All photographs or Unassigned to move individual images into a group. Create a new group first when needed. In a project, select images and Split selected to create another group. Merge moves all images into the chosen destination. These controls save immediately to `portfolio/manifests/manifest.json` and regenerate the relevant output structure. Membership changes return affected groups to pending review.

Crop review compares the original with the full-resolution clean master. Approve, reject, reset, or enter manual coordinates in the **oriented original's pixel space**: left, top, right, bottom. Right and bottom are exclusive. Crop proposals are shown in previews before approval. Tall screenshots remain flagged for interface elements even when their borders were cropped. Some photographs are physically sideways despite their metadata; these require rotation in a separate copy or a future rotation control.

Duplicate review shows hash and geometric feature candidates with their dimensions. ORB features and RANSAC supplement difference hashes for screenshot/original and cropped variants. Similarity candidates never assign site groups automatically. Choose which candidate to retain or keep the current photograph as distinct. Only exact file duplicates are excluded automatically. Distinct angles/stages remain separate. Unsuitable images are retained but excluded from the proposed gallery. Selecting a project status saves immediately. Group approval is independent of crop review; Ready status requires eligible images to have no pending crop decisions. Crop and image edits preserve group approval; membership changes require renewed grouping review. WebP files are generated for local review; `web_approved` records whether their project and crop have been approved for later use.

## Homepage gallery and Squarespace export

Tick **Homepage gallery** on retained photos in any group, or in All photographs. This shortlist is separate from project membership and hero selection; both remain unchanged. Selections save immediately and survive reruns. Untick to remove a photo. Marking a selected photo unsuitable or redundant removes it from the shortlist.

Open **Homepage gallery** to see only selected photos, then click **Download selected photos (ZIP)**. Unzip the download and upload the JPG files together into the Squarespace gallery. The ZIP contains only flat JPG image files, with unique names based on the group and stable image ID. No photos are selected automatically. An empty shortlist cannot be downloaded.

Exports use the current clean masters, including approved crops, preserve aspect ratios, and never upscale. JPEG quality and maximum long edge (90 and 2500 pixels by default) are configurable in `organiser/config.json`. Pending crops must be resolved before export. These choices follow [Squarespace's image formatting guidance](https://support.squarespace.com/hc/en-us/articles/206542517-Format-and-size-images-for-your-site); lower-resolution source photos retain their existing dimensions.

Each download also refreshes `portfolio/exports/homepage-gallery/` with the selected JPG copies and `portfolio/exports/homepage-gallery.zip`. The mapping to source assets is stored separately in `portfolio/exports/homepage-gallery-index.json`. These exports update when downloaded; previously generated copies of deselected photos are removed from this export folder. Originals, clean masters, and project galleries are preserved.

## Repeat processing

```sh
python3 organiser/workflow.py scan
python3 organiser/workflow.py qa
python3 -m unittest discover -s organiser -v
```

The scan discovers supported images recursively under this workspace, excluding `portfolio`, code, virtual environments and dependency folders. Do not put unrelated images under the source tree. The videos in `mp4` are deliberately not imported. Every source path has a stable image ID and SHA-256; identical filenames in different directories are safe. Existing group IDs and review decisions persist. New photographs stay unassigned. A changed original is reported by QA rather than replacing its recorded identity.

`organiser/config.json` controls WebP size/quality, thumbnail size, near-black detection and near-duplicate hash distance. Threshold changes affect newly imported images. Existing crop decisions are preserved; use manual review to change them. `seed_groups.py` is an optional, one-time import of the visually inspected proposals for this specific collection; it is not a general classifier or embedding model.

## Files and preservation

Originals are never written, renamed or deleted. Full-resolution clean masters are byte-for-byte source copies when no transformation is necessary, or lossless PNGs after cropping/orientation. WebP and thumbnail copies never upscale. No filters or colour correction are applied. OpenCV does not preserve embedded ICC metadata in transformed copies; colour-critical work should retain the original and use a colour-managed export step.

Each project has one primary folder under domestic, commercial, temporary-roofs or needs-review. Secondary tags live in the manifest. Exact or manually confirmed redundant images live in duplicates; all source-to-output mappings remain in the manifest. Output filenames use stable image IDs within the project folder, preventing renumbering and collisions after moves. Unassigned images live under needs-review/unassigned. Only previously registered generated paths are removed when an edit moves an image; source files are outside the output tree.

The manifest holds project evidence, provisional descriptions, content assessments, hero suggestions, dimensions, crop decisions, duplicate candidates, hashes and original filenames. `previous-manifest.json` is the previous saved edit, not a full version history. Back up the entire manifests directory before substantial review sessions. Do not run a scan concurrently with the review server or run two server instances.

Reports are in `portfolio/reports`: the initial source inventory, original and cleaned contact sheets, QA JSON and summary. Hash checks validate source preservation and generated paths. Crop safety, site identity, use category and uncertain duplicates still require human approval. No portfolio pages or final SEO case studies are generated.

## Read-only client review on Netlify

The generated **client-review/** folder is a standalone client page. It shows retained photographs in your current groups and primary categories, with hero and homepage-shortlist labels. Categories that are still Needs review appear as Category to confirm. Empty groups and unsuitable/redundant photographs are omitted. Any remaining unassigned photographs appear separately. Search, category/shortlist filters and the large-image viewer are browsing tools only: no edits or backend are available.

To update the client snapshot after making changes in the local organiser:

```sh
python3 organiser/export_client_review.py
```

This exporter requires only Python's standard library and copies existing cropped WebP images and thumbnails. It never changes the source collection or review manifest. The static snapshot is deliberately committed to Git so Netlify does not need to run the image-processing pipeline.

Commit and push **client-review/**, **netlify.toml**, **organiser/export_client_review.py**, **organiser/client-review/** and the README changes to your GitHub repository. The exporter/template files are for future local updates; only client-review is published.

In Netlify, import the existing GitHub repository **netotaku/rc-gallery**, select **main**, and use these settings (already declared in netlify.toml):

| Setting | Value |
| --- | --- |
| Base directory | `client-review` |
| Build command | Leave empty |
| Publish directory | `.` (relative to the base directory) |

The base directory also keeps Netlify from installing the local organiser's root-level Python requirements. Netlify checks out the Git repository but only deploys files inside the configured publish directory. Existing original images and local manifests already tracked in Git remain in your repository; they are not part of the published site. See [Netlify's build configuration documentation](https://docs.netlify.com/build/configure-builds/overview/) for the publish-directory behavior.

After the initial Netlify connection, pushing an updated snapshot to main triggers deployment. The client site is a snapshot: edits in your local app become visible to the client only after export, commit and push. No Netlify account credentials are stored in this project. Search indexing is discouraged with robots.txt and noindex headers; this does not add password protection.

For a local preview without the editing backend:

```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory client-review
```

Open http://127.0.0.1:8766. You can also open client-review/index.html directly in your browser.
