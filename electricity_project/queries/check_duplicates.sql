SELECT dataset_type, source_id, year_be, TRIM(category) AS category,
       TRIM(scope) AS scope, TRIM(metric) AS metric, TRIM(unit_original) AS unit,
       COUNT(*) AS duplicate_count
FROM all_observations
GROUP BY dataset_type, source_id, year_be, TRIM(category), TRIM(scope), TRIM(metric), TRIM(unit_original)
HAVING COUNT(*) > 1;
