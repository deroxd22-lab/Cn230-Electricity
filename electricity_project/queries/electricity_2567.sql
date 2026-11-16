SELECT id, year_be, category, quantity_original AS quantity, unit_original
FROM electricity
WHERE year_be = 2567
ORDER BY id;
