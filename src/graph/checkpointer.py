import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from src.config import StorageConfig

def get_checkpointer() -> SqliteSaver:
    """
    Create and return an SQLite checkpointer.
    
    Note: We use a persistent connection here. In a production multi-threaded 
    environment, you'd manage this connection lifecycle more carefully.
    """
    conn = sqlite3.connect(StorageConfig.SQLITE_CHECKPOINT_PATH, check_same_thread=False)
    return SqliteSaver(conn)
