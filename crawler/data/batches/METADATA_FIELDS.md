# Metadata Fields (`metadata_batch_XXXX.json`)

This file explains how each metadata field is calculated in simple terms.

## Top-level fields

- `batch`
  - The batch number being written.
  - Comes from `next_batch_idx` at export time.

- `generated_at`
  - Unix timestamp (`time.time()`) when this metadata file was written.

- `pages_in_batch`
  - Number of page records written in this batch file.
  - Calculated as `len(pages_buffer)` at export.
  - This is batch-only (not cumulative).

- `edges_in_batch`
  - Number of edge records written in this batch file.
  - Calculated as `len(edges_buffer)` at export.
  - This is batch-only (not cumulative).

- `stats`
  - Running counters for the whole crawl so far (cumulative across batches and resumes).
  - Not reset each batch.

- `timings`
  - Time durations captured at export.

## `stats` fields (cumulative)

- `discovered`
  - Increments when a URL is successfully pushed to frontier.
  - Includes seed URLs + accepted outlinks.

- `attempted`
  - Increments when crawler takes a URL from frontier and marks it visited.
  - This is the number of URLs actually attempted.

- `fetched_200`
  - Increments when HTTP fetch returns status code `200`.

- `parsed`
  - Increments when HTML parsing succeeds.

- `kept_after_quality`
  - Increments when parsed page passes:
  - minimum text length (`MIN_TEXT_CHARS`) and geology score (`>= GEOLOGY_THRESHOLD`).

- `duplicates_content`
  - Increments when page content hash already exists (exact content duplicate).

- `kept_after_dedup`
  - Increments when page passes content dedup check.

- `final_usable`
  - Increments when page is fully accepted and added to `pages_buffer`.
  - This is your accepted page count toward `TARGET_PAGES`.

- `duplicates_url`
  - Increments if popped URL is already in visited URL set.

- `blocked_robots`
  - Increments when robots.txt disallows a URL.

- `non_html`
  - Increments when fetch is `200` but body is not accepted HTML (`html=None`).

- `errors`
  - Increments on request exceptions or parser exceptions.

## `timings` fields

- `crawl_elapsed_sec`
  - `time.time() - crawl_start_ts`
  - Total crawl runtime since crawl state start (can include previous runs after resume).

- `batch_elapsed_sec`
  - `time.time() - batch_start_ts`
  - Time since current batch started buffering pages.

## Important interpretation note

- `pages_in_batch` and `edges_in_batch` are per-batch values.
- Most `stats.*` values are cumulative.
- So it is normal for:
  - `pages_in_batch` in batch 2 to be smaller than `stats.final_usable` in batch 2.
  - Example: if batch 1 had 42 pages and batch 2 has 195 pages, then `final_usable` can be `237`.
