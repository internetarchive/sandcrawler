
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
  SELECT sha1hex, row_to_json(file_meta)
  FROM file_meta
  ORDER BY sha1hex ASC
)
TO '/grande/snapshots/file_meta_dump.tsv'
WITH NULL '';

ROLLBACK;
