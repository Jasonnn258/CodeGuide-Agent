# CodeGuide-Agent Dataset Quality Report

- total_tasks: 100
- overall_status: pass
- history_index_available: True

## Metadata Completeness

- total_tasks: 100
- missing_field_counts: (none — all required fields populated)

## File / Directory Presence

| artifact | present_count | out_of |
|----------|---------------|--------|
| metadata_json_present | 100 | 100 |
| issue_md_present | 100 | 100 |
| gold_patch_present | 100 | 100 |
| readme_md_present | 20 | 100 |
| src_dir_present | 20 | 100 |
| tests_dir_present | 100 | 100 |
| tests_hidden_dir_present | 100 | 100 |

## By Source

| value | count |
|-------|-------|
| handcrafted | 20 |
| manual_p32_expansion | 5 |
| manual_p38_expansion | 5 |
| manual_p42_expansion | 10 |
| manual_p50_expansion | 10 |
| manual_p55_expansion | 10 |
| manual_p61_expansion | 40 |

## By Split

| value | count |
|-------|-------|
| train | 100 |

## By Difficulty

| value | count |
|-------|-------|
| easy | 96 |
| medium | 4 |

## By bug_type

| value | count |
|-------|-------|
| boundary_condition | 5 |
| cache_key | 5 |
| cache_state | 1 |
| case_insensitive_handling | 5 |
| cli_argument | 1 |
| cli_argument_propagation | 5 |
| config_merge | 4 |
| cross_file_call_chain | 1 |
| data_processing | 1 |
| date_boundary | 4 |
| dict_mutation | 4 |
| error_handling | 6 |
| idempotency | 4 |
| json_config_parsing | 5 |
| multi_file_integration | 5 |
| numeric_edge_case | 5 |
| optional_default_args | 5 |
| parser_config | 1 |
| parsing_edge_case | 4 |
| path_handling | 5 |
| service_helper_integration | 5 |
| sorting_filtering | 6 |
| stateful_side_effect | 4 |
| string_normalization | 5 |
| validation_logic | 4 |

## By generator_family

| value | count |
|-------|-------|
| advanced_repair | 7 |
| basic_repair | 6 |
| complex_repair | 19 |
| config_parsing | 12 |
| data_parsing | 3 |
| edge_case_empty | 3 |
| edge_case_none | 2 |
| error_handling | 5 |
| filtering | 2 |
| formatting | 4 |
| helper_function | 8 |
| import_handling | 3 |
| intermediate_repair | 3 |
| missing_implementation | 1 |
| parsing | 8 |
| path_handling | 3 |
| sorting | 4 |
| text_transform | 4 |
| validation | 2 |
| version_handling | 1 |

## Patch Hash Duplicates

_(no duplicate patch_hash across distinct task_ids)_

## Issue Pattern Hash Duplicates

_(no duplicate issue_pattern_hash across distinct task_ids)_

## Gold Files Overlap Groups

_(no exact gold_files list shared by 2+ tasks)_

## Gold Functions Overlap Groups

- ['make_cache_key']: task_023, task_043, task_063
- ['load_config']: task_001, task_026
- ['main']: task_015, task_027
- ['is_valid_username']: task_039, task_059
- ['merge_config']: task_040, task_060

## Template Leakage Risk Pairs

Distinct task_ids sharing generator_family AND (patch_hash OR issue_pattern_hash).

_(no template-leakage risk pairs detected)_

## Flags

- has_metadata_for_all_tasks: True
- patch_hash_duplicate_groups: 0
- issue_pattern_hash_duplicate_groups: 0
- gold_files_overlap_groups: 0
- gold_functions_overlap_groups: 5
- template_leakage_risk_pair_count: 0
- history_index_available: True

