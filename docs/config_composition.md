# 🛠 Configuration Composition

*immich2gpx* supports modular and reusable YAML configurations.
Split large configurations into multiple files with `!include` and use `references` / `!ref` for reusable fragments.

See also: [Configuration Schema](config_schema.md), [Usage Overview](usage.md)

## 📂 `!include` – Including Configuration Files

Large configurations can be organized into multiple YAML files using `!include`.
This makes your setup more modular, easier to maintain, and allows reusing common fragments across different jobs or environments.

### Example

Main file [example_include.yaml](../config/example_include.yaml):
```yaml
immich:
  url: https://your-immich-server.example.com
  api_key: !include includes/apikey.txt

references:
  - !include includes/shared_references.yaml

jobs:
  - !include includes/jobs1.yaml
  - !include includes/jobs2.yaml
```

Included files:
- [apikey.txt](../config/includes/apikey.txt):
    ```yaml
    YOUR_API_KEY
    ```

- [shared_references.yaml](../config/includes/shared_references.yaml):
    ```yaml
    my_camera:
      model: Canon EOS 123
    ```

- [jobs1.yaml](../config/includes/jobs1.yaml):
    ```yaml
    vacation:
      filter:
        or:
          country: Italy
    ```

- [jobs2.yaml](../config/includes/jobs2.yaml):
    ```yaml
    recents:
      filter:
        and:
          takenAfter: 2026-01-01T00:00:00
    ```

### Behavior

- Included files are loaded **recursively** and merged into the configuration.
- Paths are resolved **relative to the including file**.
- Only files **within the same directory tree** are allowed for security reasons.
- Includes can be nested.

## 🔖 `references` / `!ref` – References

References allow you to define reusable configuration fragments.
References are defined using a `references` section.
A `ref` replaces the node with the referenced content.

### Example

File [example_references.yaml](../config/example_references.yaml):
```yaml
# ...
references:
  my_camera:
    model: Canon EOS 123
  high_rating:
    or:
      - rating: 4
      - rating: 5
jobs:
  main:
    references:
      new_photos:
        takenAfter: 2026-03-15T12:00:00
    filter:
      and:
        - ref: my_camera
        - ref: high_rating
        - ref: new_photos
```

### Behavior

- References are defined in a `references` section.
- A `ref` replaces the node with the referenced content.
- References are resolved **recursively**, allowing composition.
- Local references are **scoped to the block** in which they are defined.
- Local references **extend** the currently available references.

### Rules and Constraints

- `references` sections are **allowed on the top level and for job definitions**.
- Reference names must be **unique within the same scope**.
- Duplicate definitions in the same scope will raise an error.
- Circular references are not allowed and will raise an error.
- Referencing an undefined name will raise an error.
