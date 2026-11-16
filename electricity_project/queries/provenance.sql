SELECT e.id, e.year_be, e.category, e.quantity_original AS quantity,
       e.unit_original, e.source_reference, s.source_name, s.source_url
FROM electricity AS e
JOIN sources AS s ON e.source_id = s.source_id
WHERE e.year_be = 2567
ORDER BY e.id;
