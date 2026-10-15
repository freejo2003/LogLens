# LogLens entity relationship diagram

This diagram records the repository's current relational model. User-owned data remains isolated by owner checks in views and services. A `Workspace` is currently owned by one user; reviewer sharing and membership tables are not implemented.

```mermaid
erDiagram
    USER ||--o{ WORKSPACE : owns
    USER ||--o{ SOURCE_FILE : owns
    USER ||--o{ SAVED_SEARCH : owns
    USER ||--o{ INDICATOR_RULE : owns
    USER ||--o{ SEARCH_RUN : starts
    USER ||--o{ BENCHMARK_RUN : starts
    USER ||--o{ ERROR_GROUP : owns
    USER o|--o{ AUDIT_EVENT : acts

    WORKSPACE ||--o{ SOURCE_FILE : contains
    WORKSPACE ||--o{ SAVED_SEARCH : scopes
    WORKSPACE ||--o{ INDICATOR_RULE : configures
    WORKSPACE ||--o{ SEARCH_RUN : records
    WORKSPACE ||--o{ BENCHMARK_RUN : records
    WORKSPACE ||--o{ ERROR_GROUP : groups
    WORKSPACE o|--o{ AUDIT_EVENT : records

    SOURCE_FILE ||--o{ TEXT_SEGMENT : extracts
    SOURCE_FILE o|--o{ SAVED_SEARCH : snapshots
    SOURCE_FILE o|--o{ SEARCH_RUN : searches
    SOURCE_FILE o|--o{ BENCHMARK_RUN : benchmarks
    SOURCE_FILE ||--o{ MATCH_RESULT : locates
    SOURCE_FILE ||--o{ GROUP_MEMBER : contributes

    INDICATOR_RULE o|--o{ SEARCH_RUN : explains
    SEARCH_RUN ||--o{ MATCH_RESULT : returns
    TEXT_SEGMENT ||--o{ MATCH_RESULT : locates
    ERROR_GROUP ||--o{ GROUP_MEMBER : includes
    TEXT_SEGMENT ||--o{ GROUP_MEMBER : represents
    BENCHMARK_RUN ||--|{ ALGORITHM_METRIC : measures

    USER {
        bigint id PK
        string username UK
    }
    WORKSPACE {
        bigint id PK
        bigint owner_id FK
        string name
    }
    SOURCE_FILE {
        bigint id PK
        bigint owner_id FK
        bigint workspace_id FK
        string storage_key UK
        string checksum
        string extraction_status
    }
    TEXT_SEGMENT {
        bigint id PK
        bigint source_file_id FK
        int sequence
        text text
        int page_number
        int paragraph_number
        int line_number
    }
    INDICATOR_RULE {
        bigint id PK
        bigint owner_id FK
        bigint workspace_id FK
        string name
        text pattern
        boolean is_active
    }
    SAVED_SEARCH {
        bigint id PK
        bigint owner_id FK
        bigint workspace_id FK
        bigint source_file_id FK
        text pattern
        string algorithm
        string source_checksum
    }
    SEARCH_RUN {
        bigint id PK
        bigint owner_id FK
        bigint workspace_id FK
        bigint source_file_id FK
        bigint indicator_rule_id FK
        text pattern
        string status
        int total_match_count
    }
    MATCH_RESULT {
        bigint id PK
        bigint search_run_id FK
        bigint source_file_id FK
        bigint segment_id FK
        json positions
        int match_count
    }
    ERROR_GROUP {
        bigint id PK
        bigint owner_id FK
        bigint workspace_id FK
        text normalized_message
        int occurrence_count
    }
    GROUP_MEMBER {
        bigint id PK
        bigint error_group_id FK
        bigint source_file_id FK
        bigint segment_id FK
    }
    BENCHMARK_RUN {
        bigint id PK
        bigint owner_id FK
        bigint workspace_id FK
        bigint source_file_id FK
        text pattern
        string input_checksum
        string status
    }
    ALGORITHM_METRIC {
        bigint id PK
        bigint benchmark_run_id FK
        string algorithm
        int trial_count
        float preprocessing_median_seconds
        float search_median_seconds
        float total_median_seconds
        bigint peak_memory_bytes
    }
    AUDIT_EVENT {
        bigint id PK
        bigint actor_id FK
        bigint workspace_id FK
        string action
        string object_type
        string object_id
        datetime created_at
    }
```

The current schema stores saved configurations and execution records independently; it does not maintain a foreign key from a rerun to its saved-search record. `SearchRun` and `SavedSearch` each target one source file today; multi-file scopes remain a product gap.
