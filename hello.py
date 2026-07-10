import sqlite3

def create_database():
    conn = sqlite3.connect('recruiter_workflow.db')
    cursor = conn.cursor()
    
    with open('schema.sql', 'r') as file:
        sql_script = file.read()
    
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()
