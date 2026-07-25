# 📐 Configuration Schema

The *immich2gpx* configuration YAML has the following main sections:

- [`immich`](#immich-server-settings) – Server URL and API key
- [`analysis`](#analysis-metadata-analysis) – Metadata fields for display and grouping
- [`gpx`](#️-gpx-gpx-export) – GPX export settings
- [`references`](#references-reusable-filter-fragments) – Reusable filter fragments
- [`jobs`](#jobs-job-definitions) – Query jobs

See also: [Configuration Composition](config_composition.md), [Usage Overview](usage.md)

The example configurations shown below are also included in the file [example_schema.yaml](../config/example_schema.yaml):

## 🔑 `immich` – Server Settings

This section defines the Immich server connection, including the server URL, API key, and HTTP timeout settings.

```yaml
immich:
  url: https://your-immich-server.example.com
  api_key: YOUR_API_KEY
  timeout: 10
```

| Key       | Description                                                |
| --------- | ---------------------------------------------------------- |
| `url`     | Base URL of the Immich server                              |
| `api_key` | Immich API key ([Immich API Key Setup](immich_api_key.md)) |
| `timeout` | HTTP request timeout in seconds                            |

## 📊 `analysis` – Metadata Analysis

This section configures which metadata fields are displayed or grouped when analyzing or comparing media.

```yaml
analysis:
  show_keys:
    - id
    - fileCreatedAt
    - originalFileName
    - people
  group_by_keys:
    - originalPath
    - model
    - country
```

| Key             | Description                                               |
| --------------- | --------------------------------------------------------- |
| `show_keys`     | Fields displayed when using `--show` and `--compare-with` |
| `group_by_keys` | Fields used for grouping when using `--group`             |

> 🔗 For a full list of supported metadata fields for `show_keys` and `group_by_keys`, refer to the Immich API documentation.
> You can use metadata keys from both the asset and the asset's EXIF:
> - https://api.immich.app/models/AssetResponseDto
> - https://api.immich.app/models/ExifResponseDto

## 🗺️ `gpx` – GPX Export

This section specifies the GPX export options, including the output directory and which metadata fields are included in the track points.

```yaml
gpx:
  directory: gpx
  description_keys:
    - id
    - originalFileName
    - model
```

| Key                | Description                               |
| ------------------ | ----------------------------------------- |
| `directory`        | Output directory for GPX files            |
| `description_keys` | Metadata fields added to GPX descriptions |

`directory` can be an absolute path or relative to the current working directory.

> 🔗 For a full list of supported metadata fields for `description_keys`, refer to the Immich API documentation.
> You can use metadata keys from both the asset and the asset's EXIF:
> - https://api.immich.app/models/AssetResponseDto
> - https://api.immich.app/models/ExifResponseDto

The GPX output consists of:
- One GPX file per standalone job, i.e., for the selected main job, and for each job defined as `run_jobs`
- One `<trk>` per GPX file
- One `<trkseg>` per Immich server query
- One `<trkpt>` per media item

## 🔖 `references` – Reusable Filter Fragments

This section contains reusable configuration fragments that can be referenced throughout jobs and filters.
References allow you to define modular and maintainable configurations by reusing common filters or settings across multiple jobs.

For detailed examples of including and using references, see [Configuration Composition](config_composition.md#references-ref-references).

## ⚡ `jobs` – Job Definitions

This section defines the tasks for querying media, applying filters, and exporting the results.

```yaml
jobs:
  main:
    merge_jobs: # ...
    run_jobs: # ...
    references: # ...
    filter: # ...
```

| Key          | Description                                                                                                     |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| `merge_jobs` | Merge results from other jobs matching a pattern ([Job Composition](#job-composition))                          |
| `run_jobs`   | Execute other jobs matching a pattern ([Job Composition](#job-composition))                                     |
| `references` | Job-specific reusable references ([Configuration Composition](config_composition.md#references-ref-references)) |
| `filter`     | Filter for Immich server query ([Job Filter](#job-filter))                                                      |

### Job Composition

Jobs can combine or run other jobs.

```yaml
jobs:
  main:
    merge_jobs: vacation-202?
    run_jobs:
      - new_favorite_photos
      - special_filter_*
    # ...
```

The example above will lead to the following behavior:
- `merge_jobs`:
    - Query results for jobs that match `vacation-202?` will be merged into main.
    - For example, this includes `vacation-2025` but not `vacation-2019`.
- `run_jobs`:
    - Query results for jobs that match `new_favorite_photos` and `special_filter_*` will be executed but not merged.
    - For example, this includes `new_favorite_photos` and `special_filter_123`.
- *immich2gpx* will generate three GPX files in this case:
    - `main.gpx`, including the data from `vacation-2025.gpx`
    - `new_favorite_photos.gpx`
    - `special_filter_123.gpx`

Internally, *immich2gpx* uses a modified Depth-First Search (DFS) algorithm to build the job dependency graph.

Use the following syntax for job name pattern matching or refer to [fnmatch](https://docs.python.org/3/library/fnmatch.html):

- `*` for any number of characters
- `?` for a single character
- `[seq]` for any character in `seq` (e.g., `[0-9]` for digits)
- `[!seq]` for any character not in `seq`

### Job Filter

Filters define search conditions for querying assets based on Immich metadata fields.

```yaml
jobs:
  main:
    # ...
    references:
      my_camera:
        model: Canon EOS 123
    filter:
      and:
        - ref: my_camera
        - originalFileName: jpg
        - and:
            - takenAfter: 2026-01-01T00:00:00
            - or:
                - createdAfter: 2026-01-31T23:59:59
                - takenBefore: 2026-01-31T23:59:59
        - or:
            - country: Italy
            - country: Spain
            - personIds: ["44fe826f-11d1-45f0-bb6e-a22d40fc16eb"]
            - rating: 5
```

Filters support two Boolean logic operators:
- `and`: All conditions must match
- `or`: Any condition can match

The operators can be used as follows:
- **The top-level `filter` must contain exactly one top-level logical operator.**
- Below this level, there can be an arbitrary number of operators or metadata fields.
- Operators can be **nested arbitrarily** to express complex queries.

Internally, filters are transformed into Disjunctive Normal Form (DNF), i.e., a series of OR-conditions.
Each OR condition represents a query sent to the Immich server, which is a conjunction, i.e., AND-combination, of metadata property conditions.

> 🔗 Field names correspond directly to properties supported by the Immich search API.
> Refer to the Immich API documentation to find available filter properties:
> https://api.immich.app/endpoints/search/searchAssets

Filter values must match the expected data types of the Immich API.
Below are the common types and how they are represented in YAML:

- `String`:
    ```yaml
    model: Canon EOS 123
    country: "Italy"
    ```

- `Number`:
    ```yaml
    rating: 5
    ```

- `DateTime` (ISO-8601):
    ```yaml
    takenBefore: 2026-01-15T08:00:00
    updatedAfter: 2025-12-01T14:00:00
    ```

- `Boolean`:
    ```yaml
    isFavorite: true
    isArchived: false
    ```

- `Null`:
  ```yaml
  city: null
  ```

- `UUID` Array (Immich `UUID[]`, must be a list):
    ```yaml
    personIds:
      - "44fe826f-11d1-45f0-bb6e-a22d40fc16eb"
    albumIds:
      [
        "c844e26a-508a-40fe-8440-e1328c1b10a7",
        "9a289e44-2b39-493d-8e0a-fd418ad133db",
      ]
    ```
