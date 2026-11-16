SELECT dataset_type, COUNT(*) AS observation_count
FROM all_observations
GROUP BY dataset_type
ORDER BY dataset_type;
