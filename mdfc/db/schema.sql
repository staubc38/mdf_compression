-- duckdb schema to save data from an MDF file
-- there is a "unified time axis" collected from all groups, 
--  which will be saved in a table "time", 
-- other tables will be required... TBD!

CREATE SEQUENCE times_id_seq START 1 INCREMENT BY 1;
CREATE TABLE mdf_timestamps(
    -- interestingly... specifying these compressions seems to increase the file size!
    -- at least, on just testing 50k rows of ascending float values
    -- could work out as we add more data though...
    -- and, perhaps we can 
    ID BIGINT PRIMARY KEY DEFAULT nextval('times_id_seq') USING COMPRESSION pfor,
    mdf_timestamp DOUBLE USING COMPRESSION patas
    -- mdf_timestamp INTEGER USING COMPRESSION pfor  -- testing integer compression
);
