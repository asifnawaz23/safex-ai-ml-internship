# Testing and Validation

## Latest test run

- **Command (repository root):** `.\.venv\Scripts\python.exe -m pytest -q -rxXs`
- **Environment:** Windows 11, Python 3.13.5, pytest 8.4.2.
- **Configuration:** `pytest.ini` sets `pythonpath = src` and `-p no:cacheprovider`.

```
193 passed, 4 xfailed in 8.50s
```

A second run with `-v` gave the same 193 passed and 4 xfailed (7.47 s). The final audit, after regenerating every artifact from a clean state, gave 193 passed and 4 xfailed with `pytest -q` (8.33 s) and again via `python -m pii_pipeline.cli test` (7.66 s). The SHA-256 of `output/pipeline.log` was identical before and after the test run, so the tests do not write to the repository log.

| File | Collected | Passed | Failed | Skipped | XFAIL (strict) |
|---|---|---|---|---|---|
| `tests/test_synthetic_data.py` | 22 | 22 | 0 | 0 | 0 |
| `tests/test_recognizers.py` | 80 | 80 | 0 | 0 | 0 |
| `tests/test_redaction.py` | 29 | 29 | 0 | 0 | 0 |
| `tests/test_evaluation.py` | 15 | 15 | 0 | 0 | 0 |
| `tests/test_privacy.py` | 23 | 23 | 0 | 0 | 0 |
| `tests/test_integration.py` | 5 | 5 | 0 | 0 | 0 |
| `tests/test_regression.py` | 23 | 19 | 0 | 0 | 4 |
| **Total** | **197** | **193** | **0** | **0** | **4** |

The 4 expected failures are deliberate. They assert the *desired* detection for the name misses DM-009 to DM-012, which are not fixed:

- `test_dm_person_lowercase_name_expected_miss`
- `test_dm_person_unlabelled_in_prose_expected_miss`
- `test_dm_person_three_token_signature_expected_miss`
- `test_dm_person_uppercase_name_expected_miss`

Each is marked `strict=True` with the reason "NOT FIXED BY DESIGN: en_core_web_sm limitation". If one of them started to pass, pytest would report XPASS as a failure.

## Coverage of the 20 required areas

| # | Area | Tests (examples) |
|---|---|---|
| 1 | Dataset count and uniqueness | `test_at_least_800_records`, `test_count_is_configurable`, `test_record_ids_and_texts_unique` |
| 2 | Ground-truth span integrity | `test_every_span_matches_text`, `test_offsets_are_end_exclusive`, `test_validate_annotations_detects_bad_offset`, `test_traps_never_overlap_ground_truth` |
| 3 | Category coverage | `test_all_seven_entity_types_present`, `test_all_document_types_present`, `test_no_category_dominates` |
| 4 | PK phone positives | `test_pk_phone_positive[...]`, `test_pk_phone_detected_by_improved_engine[...]` |
| 5 | PK phone negatives | `test_pk_phone_negative[...]`, `test_builtin_phone_recognizer_flags_plain_10_digits` (documents a built-in false positive) |
| 6 | CNIC positives | `test_cnic_hyphenated_without_context`, `test_cnic_plain_with_context[...]`, `test_cnic_hyphenated_in_sentence` |
| 7 | CNIC negatives | `test_cnic_negative_patterns[...]`, `test_cnic_plain_without_context_below_threshold`, `test_cnic_repeated_digit_invalidated` |
| 8 | Email | `test_email_detected[...]`, `test_email_not_flagged_without_at_sign` |
| 9 | Person | `test_labelled_person_pattern[...]`, `test_labelled_person_is_case_sensitive`, `test_labelled_person_excludes_stop_tokens`, `test_person_detected_by_improved_engine` |
| 10 | Address and postal code | `test_address_pattern[...]`, `test_landmark_address_not_targeted`, `test_postal_positive[...]`, `test_postal_negative[...]`, `test_address_and_adjacent_postal_engine` |
| 11 | Customer ID | `test_customer_id_positive[...]`, `test_customer_id_negative[...]` |
| 12 | Redaction correctness | `test_single_phone_replaced_exactly`, `test_operator_per_label[...]`, `test_unknown_label_uses_fallback`, `test_custom_phone_and_cnic_redacted_by_engine`, `test_location_mapped_to_address_placeholder` |
| 13 | Documents with no detection | `test_no_predictions_returns_text_unchanged`, `test_trap_only_document_unchanged_by_improved` |
| 14 | Multiple entities | `test_multi_entity_document` |
| 15 | Overlapping detections | `test_overlapping_different_labels_leave_no_original_characters`, `test_partially_overlapping_spans_fully_covered`, `test_nested_same_label_gives_single_placeholder` |
| 16 | Residual verification | `test_residual_found_when_value_survives`, `test_residual_none_after_redaction`, `test_residual_digits_with_other_separators`, `test_residual_email_case_insensitive`, `test_residual_respects_boundaries`, `test_partial_redaction_reported_as_residual_free_only_if_value_gone`, `test_partial_leak_counted_next_to_value_residuals` |
| 17 | Precision and recall on hand-checkable examples | `test_exact_match_is_tp`, `test_wrong_label_counts_fn_and_fp`, `test_partial_overlap_not_tp_but_overlap_recall`, `test_duplicate_prediction_is_fp`, `test_one_prediction_cannot_match_two_gt`, `test_identical_values_twice_both_need_predictions`, `test_nested_ground_truth_independent_targets`, `test_hand_computed_precision_recall_f1`, `test_zero_denominators_are_na` |
| 18 | Baseline and improved integration | `tests/test_integration.py` (5 tests: every record processed, engine metadata, improved beats baseline on local identifiers, fewer residuals, report columns) |
| 19 | Deterministic generation | `test_same_seed_identical`, `test_different_seed_differs`, `test_saved_files_hash_identical`, `test_matching_is_deterministic_under_input_order` |
| 20 | No raw PII in ordinary logs | `test_pipeline_logs_contain_no_planted_values` (caplog), `test_log_filter_masks_pii_like_strings`, `test_source_never_logs_record_text`, `test_test_runs_do_not_write_to_repo_log_file` |

Other tests:

- **Unicode, punctuation and idempotency** (`tests/test_redaction.py`):
  - `test_unicode_urdu_text_preserved`, `test_urdu_text_full_engine_redacts_phone`, `test_accented_text_preserved`
  - `test_punctuation_and_whitespace_preserved`, `test_repeated_occurrences_all_replaced`, `test_redacting_redacted_text_is_idempotent`
- **Privacy guards** (`tests/test_privacy.py`):
  - paths and files: `test_path_traversal_refused`, `test_disallowed_extension_refused`, `test_user_input_file_must_be_under_data`, `test_load_dataset_refuses_outside_data_dir`, `test_output_separation`
  - synthetic-only checks: `test_synthetic_guard_*`, `test_rows_must_be_marked_synthetic`, `test_document_length_limit`
  - HMAC: `test_hmac_requires_key`, `test_hmac_deterministic_and_key_dependent`
  - network and code safety: `test_analysis_makes_no_network_connections`, `test_no_eval_exec_or_network_imports_in_src`
  - CLI: `test_cli_redact_refuses_real_looking_email`, `test_cli_redact_dry_run_masks_values`, `test_cli_redact_output_must_stay_in_output_redacted`
- **Regressions** (`tests/test_regression.py`):
  - prototype bugs: `test_d1_*` to `test_d5_*`
  - dangerous-miss fixes: `test_dm_*`
  - company-code allow-list: `test_fp_company_codes_not_redacted`

## Other verification performed

| Check | Result |
|---|---|
| `python -m pii_pipeline.cli all` | Exit 0 in each of 3 consecutive runs (build-loop verification). The final artifacts come from the third run. |
| Reproducibility | Two consecutive `all` runs produced byte-identical dataset, prediction, redacted, chart and metric files. The exceptions are the four runtime-bearing files: `experiment_summary.csv`, `summary.json` and `*_engine.json`. |
| Ground-truth offsets | `summary.json`: `all_offsets_valid: true`, 3412 annotations, 1038 traps |
| CLI checks run during the docs step | All exit codes are as documented. |
| Log content | After the final CLI run, `output/pipeline.log` contained 0 of the 3176 distinct planted values of 5 or more characters (build-loop verification). |

The CLI checks from the docs step:

| Command | Exit code | Result |
|---|---|---|
| `redact --text "...0321-1234567..." --dry-run` | 0 | masked preview |
| `redact --text` with a multi-entity synthetic sentence | 0 | all 7 types replaced |
| `redact --text "mail me at a@gmail.com"` | 2 | refused |
| `redact --record-id REC-00008` | 0 | redacted output |

## Checks not performed

- No test on real documents. By design, the project processes synthetic data only.
- No run on Linux or macOS, and no run on any Python other than 3.13.5.
- No clean install into a brand-new virtual environment during the docs step. The existing `.venv` matches `requirements.txt`, which was checked with `pip install -r requirements.txt --dry-run` in the build step.
- No peer review yet (PENDING, see `docs/PEER_REVIEW.md`).
- No code-coverage measurement. `pytest-cov` is installed in the venv but is not a project requirement and was not used.
- No performance or load testing beyond the recorded runtime of 870 records.
- No formal verification that third-party libraries make no network calls. The network test covers the analysis path it exercises.

## Limitations of the test suite

- Recogniser tests use formats chosen by the same author who wrote the patterns. Passing them shows that the patterns behave as designed, not that they generalise.
- The integration tests run on a generated subset, not the full 870 records. The full evaluation runs through the CLI.
- The residual tests check planted values only. Nothing can test for PII that nobody annotated.
