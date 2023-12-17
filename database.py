import sqlite3

SERVERS_DATABASE="servers.db"

def setup_database():
    con = sqlite3.connect(SERVERS_DATABASE)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS servers(guild PRIMARY KEY, volume)")

def store_volume(guild, volume):
    guild = str(guild.id)
    if not guild.isnumeric(): return None
    if type(volume) != float: return None

    con = sqlite3.connect(SERVERS_DATABASE)
    cur = con.cursor()
    res = cur.execute(f"SELECT volume FROM servers WHERE guild='{guild}'")
    if res.fetchone() == None:
        # If guild isnt in servers yet, add it
        print("Adding in value")
        cur.execute(f"""
            INSERT INTO servers VALUES
            ('{guild}', {volume})
        """)
    else:
        # Update guilds row
        cur.execute(f"""
            UPDATE servers
            SET volume = {volume}
            WHERE guild='{guild}'
        """)
    con.commit()

def retrieve_volume(guild):
    guild = str(guild.id)
    if not guild.isnumeric(): return None
    con = sqlite3.connect(SERVERS_DATABASE)
    cur = con.cursor()
    res = cur.execute(f"SELECT volume FROM servers WHERE guild='{guild}'")
    volume = res.fetchone()
    if volume == None:
        set_volume(guild, 1.0)
        return 1.0

    return volume[0]
