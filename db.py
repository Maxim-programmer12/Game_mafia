import sqlite3
import random
from pathlib import Path
from traceback import print_exc

Base_dir = Path(__file__).resolve().parent
DB_path = Base_dir / "Для_mafia.db"
# декоратор для авто-подключения, -отката и -сохранения в БД.
def connect(func):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect(str(DB_path))
        cur = conn.cursor()
        result = None

        try:
            result = func(cur, *args, **kwargs)
            conn.commit()
        except Exception:
            conn.rollback()
            print(f"[ERROR]: {func.__name__}: {print_exc()}")
        finally:
            conn.close()
        return result
    return wrapper
# создаём БД если нет её.
@connect
def init_db(cur):
    # таблица с игроками.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                username TEXT,
                role TEXT DEFAULT 'citizen',
                dead INTEGER DEFAULT 0,
                voted INTEGER DEFAULT 0
    )""")
    # таблица с голосованиями.
    cur.execute("""
                CREATE TABLE IF NOT EXISTS votes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vote_type TEXT NOT NULL,
                target_name TEXT NOT NULL,
                voted_id INTEGER NOT NULL,
                FOREIGN KEY (voted_id) REFERENCES players(id)
                )
                """)
# добавляем пользователя.
@connect
def insert_player(cur, player_id : int, username : str) -> None:
    cur.execute("""
        INSERT OR REPLACE INTO players(player_id, username, dead, voted)
        VALUES (?, ?, COALESCE((SELECT dead FROM players WHERE player_id = ?), 0), 0)
        """, (player_id, username, player_id))
# считаем кол-во пользователей.
@connect
def players_amount(cur) -> int:
    cur.execute("SELECT COUNT(*) FROM players")
    return cur.fetchone()[0]
# получаем кол-во мафий.
@connect
def get_mafia_usernames(cur) -> str:
    cur.execute("SELECT username FROM players WHERE role = 'mafia' AND dead = 0")
    rows = cur.fetchall()
    return '\n'.join(row[0] for row in rows)
# получаем роли всех пользователей.
@connect
def get_players_roles(cur) -> list:
    cur.execute("SELECT player_id, role FROM players")
    return cur.fetchall()
# возвращаем живых игроков.
@connect
def get_all_alive(cur) -> list:
    cur.execute("SELECT username FROM players WHERE dead = 0")
    return [row for row in cur.fetchall()]
# "раздаём" роли игрокам.
@connect
def set_roles(cur) -> None:
    cur.execute("SELECT player_id FROM players ORDER BY player_id")
    player_rows = cur.fetchall()
    n = len(player_rows)
    if n == 0:
        return
    
    mafias = max(1, int(n * 0.3))
    roles = ["mafia"] * mafias + ["citizen"] * (n - mafias)
    random.shuffle(player_rows)
    for (player_id, ), role in zip(player_rows, roles): #zip() -> сжимает последовательности(списки) в одну(один список).
        cur.execute("UPDATE players SET role=?, dead=0, voted=0 WHERE player_id=?", (role, player_id))
# проверяем игрока на существование.
@connect
def user_exists(cur, player_id : int) -> bool:
    cur.execute("SELECT 1 FROM players WHERE player_id = ?", (player_id,))
    return cur.fetchone() is not None
# голосование за игрока(ночное и дневное).
@connect
def cast_vote(cur, vote_type : str, target_name : str, voted_id : int) -> bool:
    cur.execute("SELECT dead, voted FROM players WHERE player_id = ?", (voted_id,))
    
    row = cur.fetchone()
    if not row:
        return False
    dead, voted = row
    if dead != 0 or voted != 0:
        return False

    cur.execute("SELECT 1 FROM players WHERE username = ? AND dead = 0", (target_name,))

    if not cur.fetchone():
        return False
    
    cur.execute("""INSERT INTO votes (vote_type, target_name, voted_id) VALUES (?, ?, ?)""",
                (vote_type, target_name, voted_id)
                )
    cur.execute("UPDATE players SET voted = 1 WHERE player_id = ?", (voted_id,))
    return True
# "дело мафии" и возвращаем тех, кого она "убила".
@connect
def mafia_kill(cur) -> str:
    cur.execute("SELECT COUNT(*) FROM players WHERE role = 'mafia' and dead = 0")
    mafia_alive = cur.fetchone()[0]

    if mafia_alive == 0:
        return "Никого"

    cur.execute("""
                SELECT target_name, COUNT(*) AS count
                FROM votes
                WHERE vote_type = 'mafia'
                GROUP BY target_name
                ORDER BY count DESC
                LIMIT 1
                """)

    top = cur.fetchone()

    if not top:
        return "Никого"
    
    target, count = top
    if count == mafia_alive:
        cur.execute("UPDATE players SET dead = 1 WHERE username = ?", (target,))
        return target
    return "Никого"
# голосование мирных жителей за других игроков.
@connect
def citizen_kill(cur) -> str:
    cur.execute("""
    SELECT target_name, COUNT(*) AS count
    FROM votes
    WHERE vote_type = 'citizen'
    GROUP BY target_name
    ORDER BY count DESC
    LIMIT 2
    """)

    rows = cur.fetchall()
    if not rows:
        return "Никого"
    
    top = rows[0]
    top_username, top_count = top
    
    if len(rows) > 1 and rows[1][1] == top_count:
        return "Никого"
    
    cur.execute("UPDATE players SET dead = 1 WHERE username = ?", (top_username,))
    return top_username

if __name__ == "__main__":
    init_db()
    """insert_player(1, "Максим")
    insert_player(2, "Александр")
    insert_player(3, "Артём")
    print(f"Кол-во игроков: {players_amount()}")
    print(f"Мафии игры: {get_mafia_usernames()}")
    print(get_all_alive())
    set_roles()
    print(f"Игроки и их роли:", {*get_players_roles()})
    print(user_exists(1))
    print(cast_vote("mafia", "Александр", 3))
    print(mafia_kill())
    print(cast_vote("citizen", "Максим", 2))
    print(cast_vote("citizen", "Александр", 1))
    print(cast_vote("citizen", "Александр", 3))
    print(citizen_kill())"""
