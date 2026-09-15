import duckdb
con=duckdb.connect(); con.sql("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
q="""
COPY (
SELECT id, names.primary AS name, categories.primary AS cat, categories.alternate AS alt,
       confidence, operating_status,
       addresses[1].freeform AS addr, addresses[1].locality AS city, addresses[1].postcode AS zip,
       ST_X(ST_Centroid(geometry)) AS lon, ST_Y(ST_Centroid(geometry)) AS lat, brand.names.primary AS brand
FROM read_parquet('s3://overturemaps-us-west-2/release/2026-08-19.0/theme=places/type=place/*', hive_partitioning=1)
WHERE bbox.xmin BETWEEN -118.95 AND -117.64 AND bbox.ymin BETWEEN 33.30 AND 34.83
  AND ( categories.primary ILIKE '%korean%' OR list_contains(list_transform(categories.alternate, x->x ILIKE '%korean%'), true)
        OR names.primary ILIKE '%korean%' OR categories.primary ILIKE '%barbecue%' OR list_contains(list_transform(categories.alternate, x->x ILIKE '%barbecue%'), true) )
) TO 'overture_la.parquet' (FORMAT parquet);
"""
con.sql("INSTALL spatial; LOAD spatial;")
con.sql(q)
print(con.sql("select count(*), count(*) filter (where cat ilike '%korean%' or list_contains(list_transform(alt,x->x ilike '%korean%'),true)) from 'overture_la.parquet'"))
print(con.sql("select operating_status,count(*) from 'overture_la.parquet' group by 1"))
