# Task Expansion Spec

## Purpose

This spec defines how to add new Mini-Repo-Debug tasks without weakening benchmark quality or leaking hidden information.

## Required task files

Each task should include:

- issue.md
- metadata.json
- public tests
- hidden tests
- gold.patch
- buggy source files

## Task metadata fields

Recommended metadata:

- task_id
- bug_type
- difficulty
- issue_path
- public_test_cmd
- hidden_test_cmd
- target_files
- target_functions
- expected_failure_mode
- generalization_axis
- oracle_leakage_risk

## Bug types

Use one of:

- parsing_edge_case
- path_handling
- cache_key
- optional_default_args
- boundary_condition
- string_normalization
- dict_mutation
- date_boundary
- json_config_parsing
- cli_argument_propagation
- error_handling
- numeric_edge_case
- sorting_filtering
- service_helper_integration
- case_insensitive_handling
- multi_file_integration
- stateful_side_effect
- idempotency
- validation_logic
- config_merge

## Difficulty

easy:

- one file
- one function
- public tests reveal the main bug
- hidden tests check one boundary

medium:

- one or two files
- public tests under-specify the real condition
- hidden tests check generalization

hard:

- multi-file or semantic dependency
- public tests can be passed by a narrow patch
- hidden tests expose patch overfitting

## Good public-hidden gap examples

Example 1:

- public: default argument omitted
- hidden: explicit list argument should not be mutated

Example 2:

- public: lowercase email
- hidden: whitespace, casing, plus tag, invalid input

Example 3:

- public: simple relative path
- hidden: nested path, absolute path, parent directory

Example 4:

- public: single active item
- hidden: tie-breaking and stable ordering

## Authoring checklist

Before accepting a new task:

- Public tests fail on buggy code.
- Hidden tests fail on buggy code.
- Gold patch passes public tests.
- Gold patch passes hidden tests.
- Public tests can be passed by at least one narrow or incomplete patch.
- Hidden tests catch the narrow patch.
- No hidden test name appears in model-facing exports.
- No metadata or gold patch path appears in model-facing exports.
- Task can run offline.
- Task validation is deterministic.

## Rejection criteria

Reject a task if:

- It is too trivial.
- It has no meaningful hidden generalization gap.
- It depends on network, time, randomness, or external state.
- The issue text reveals the exact gold patch.
- Hidden tests duplicate public tests.
- The task cannot be validated quickly.
