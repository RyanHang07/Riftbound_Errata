-- Slice 0 creates the extension only. The chunks table waits for slice 2,
-- because slice 1 may change what its columns need to be (how dates are
-- sourced, whether section numbers survive between versions).
CREATE EXTENSION IF NOT EXISTS vector;
