from sqlalchemy import create_engine, text

def recover_database(engine):
    """Recover the database to a working state"""
    connection = engine.connect()
    
    try:
        # Check what tables currently exist
        tables = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
        
        table_names = [table[0] for table in tables]
        print(f"Existing tables: {table_names}")
        
        # If we have videos_new but no videos, we need to rename it back
        if 'videos_new' in table_names and 'videos' not in table_names:
            connection.execute(text("ALTER TABLE videos_new RENAME TO videos"))
            print("Renamed videos_new back to videos")
            
        # Check the current structure of the videos table
        structure = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='videos'")
        ).fetchone()
        
        if structure:
            print(f"Current table structure:\n{structure[0]}")
            
            # Ensure we have the correct columns
            if 'processed_date' not in structure[0]:
                connection.execute(text("ALTER TABLE videos ADD COLUMN processed_date DATETIME"))
                print("Added processed_date column")
            
            if 'upload_date' not in structure[0] and 'date' in structure[0]:
                # Create a backup before making changes
                connection.execute(text("CREATE TABLE videos_backup AS SELECT * FROM videos"))
                print("Created backup table videos_backup")
                
                # Create new table with correct structure
                connection.execute(text("""
                    CREATE TABLE videos_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id TEXT UNIQUE,
                        title TEXT,
                        upload_date DATETIME,
                        processed_date DATETIME
                    )
                """))
                
                # Copy data, renaming date to upload_date
                connection.execute(text("""
                    INSERT INTO videos_new (id, video_id, title, upload_date, processed_date)
                    SELECT id, video_id, title, date, processed_date FROM videos
                """))
                
                # Drop old table and rename new one
                connection.execute(text("DROP TABLE videos"))
                connection.execute(text("ALTER TABLE videos_new RENAME TO videos"))
                print("Restructured table with upload_date column")
        
        else:
            # If no videos table exists at all, create it with the correct structure
            connection.execute(text("""
                CREATE TABLE videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT UNIQUE,
                    title TEXT,
                    upload_date DATETIME,
                    processed_date DATETIME
                )
            """))
            print("Created new videos table with correct structure")
        
        connection.commit()
        print("Recovery completed successfully")
        
    except Exception as e:
        print(f"Recovery error: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    db_path = 'videos.db'
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    recover_database(engine)