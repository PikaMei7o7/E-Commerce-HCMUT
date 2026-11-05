INSERT INTO star_schema.dim_date (
    date_key, full_date, day, month, quarter, year, day_of_week
)
SELECT TO_CHAR(d.t_dat, 'YYYYMMDD')::INTEGER,
       d.t_dat,
       EXTRACT(DAY FROM d.t_dat)::SMALLINT,
       EXTRACT(MONTH FROM d.t_dat)::SMALLINT,
       EXTRACT(QUARTER FROM d.t_dat)::SMALLINT,
       EXTRACT(YEAR FROM d.t_dat)::SMALLINT,
       EXTRACT(ISODOW FROM d.t_dat)::SMALLINT
FROM (SELECT DISTINCT t_dat FROM public."transaction") AS d
ON CONFLICT (date_key) DO UPDATE SET
    full_date = EXCLUDED.full_date,
    day = EXCLUDED.day,
    month = EXCLUDED.month,
    quarter = EXCLUDED.quarter,
    year = EXCLUDED.year,
    day_of_week = EXCLUDED.day_of_week;
